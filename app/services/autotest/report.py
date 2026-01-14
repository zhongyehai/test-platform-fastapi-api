from fastapi import Request, BackgroundTasks, Depends

from app.schemas.enums import ApiCaseSuiteTypeEnum, ReceiveTypeEnum, SendReportTypeEnum
from utils.message.send_report import send_report
from ...models.autotest.model_factory import ModelSelector
from ...models.config.model_factory import Config, WebHook
from ...models.system.model_factory import User
from ...schemas.autotest import reprot as schema
from utils.util.file_util import FileUtil


async def get_report_list(request: Request, form: schema.FindReportForm = Depends()):
    models = ModelSelector(request.app.test_type)
    get_filed = models.report.get_simple_filed_list()
    if form.detail:
        get_filed.extend([
            "create_time", "trigger_type", "env", "is_passed", "process", "status", "create_user", "project_id",
            "trigger_id", "run_type", "notified", "retry_count"
        ])

    query_data = await form.make_pagination(models.report, get_filed=get_filed)
    return request.app.get_success(data=query_data)


async def save_report_as_case(request: Request, form: schema.GetReportForm = Depends()):
    models = ModelSelector(request.app.test_type)
    report_step = await models.report_step.filter(report_id=form.id).values("element_id", "name")
    if not report_step and not report_step.get("element_id"):
        ValueError("数据不存在")

    api = await models.api.filter(id=report_step["element_id"]).first()
    case_suite = await models.suite.filter(project_id=api.project_id, suite_type=ApiCaseSuiteTypeEnum.API).first()
    case = await models.case.model_create({
        "name": report_step["name"],
        "desc": report_step["name"],
        "suite_id": case_suite.id
    }, request.state.user)
    await models.step.model_create({
        "name": report_step["name"],
        "case_id": case.id,
        "api_id": api.id,
        **dict(api)
    }, request.state.user)
    return request.app.post_success()


async def notify_report(request: Request, form: schema.NotifyReportForm):
    front_host = await Config.get_report_host()
    models = ModelSelector(request.app.test_type)
    report_addr = f'{front_host}{await Config.get_api_report_addr()}'
    if request.app.test_type == "app":
        report_addr = f'{front_host}{await Config.get_app_ui_report_addr()}'
    elif request.app.test_type == "ui":
        report_addr = f'{front_host}{await Config.get_web_ui_report_addr()}'

    report = await models.report.filter(id=form.id, run_type='task', notified=False).first()
    if report:
        task_dict = dict(await models.task.filter(id=report.trigger_id[0]).first())
        # 发送渠道、默认、钉钉、企业微信、邮件
        if form.notify_to == 'email' or (form.notify_to == 'default' and task_dict["receive_type"] == ReceiveTypeEnum.EMAIL):  # 邮件
            task_dict["receive_type"] = ReceiveTypeEnum.EMAIL
            email_server = await Config.filter(name=task_dict["email_server"]).first().values("value")
            task_dict["email_server"] = email_server["value"]
            email_from = await User.filter(id=task_dict["email_from"]).first().values("email", "email_password")
            task_dict["email_from"], task_dict["email_pwd"] = email_from["email"], email_from["email_password"]
            email_to = await User.filter(id__in=task_dict["email_to"]).all().values("email")
            task_dict["email_to"] = [email["email"] for email in email_to]
        else:  # 解析并组装webhook地址并加签
            task_dict["webhook_list"] = await WebHook.get_webhook_list(task_dict["receive_type"], task_dict["webhook_list"])

        if form.notify_to != 'default':
            task_dict["is_send"] = SendReportTypeEnum.ALWAYS.value  # 手动触发发送通知的，且选择的通知渠道不是任务设置的，不管结果如何都通知

        res = await send_report(
            content_list=[{"report_id": report.id, "report_summary": report.summary}],
            **task_dict,
            report_addr=report_addr
        )
        if res is True:
            await models.report.filter(id=form.id).update(notified=True)
            return request.app.success("触发通知成功")
        elif res is False:
            return request.app.fail("通知失败，请检查通知渠道设置")
    return request.app.fail("当前报告不符合任务设置的触发通知条件")


async def get_report_suite_list(request: Request, form: schema.GetReportCaseSuiteListForm = Depends()):
    models = ModelSelector(request.app.test_type)
    suite_and_case_list = await models.report_case.get_resport_suite_and_case_list(form.report_id, models.suite, models.report_step)
    return request.app.get_success(suite_and_case_list)


async def get_report_case_list(request: Request, form: schema.GetReportCaseListForm = Depends()):
    models = ModelSelector(request.app.test_type)
    case_list = await models.report_case.get_resport_case_list(form.report_id, form.get_summary)
    return request.app.get_success(case_list)


async def get_report_case(request: Request, form: schema.GetReportCaseForm = Depends()):
    models = ModelSelector(request.app.test_type)
    data = await models.report_case.validate_is_exist("数据不存在", id=form.id)
    return request.app.get_success(data)


async def get_report_rerun_case_list(request: Request, form: schema.GetReportRerunCaseForm = Depends()):
    models = ModelSelector(request.app.test_type)
    filters = {"result__not": "success"} if form.result == "failed" else {"result": "success"}
    report = await models.report.filter(id=form.id).first().values("run_type")
    if report["run_type"] == "api":  # 如果是跑接口产生的，需要查 report_step 的 element_id
        data_list = await models.report_step.filter(report_id=form.id, **filters).all().values_list("element_id", flat=True)
    else:
        data_list = await models.report_case.filter(report_id=form.id, **filters).all().values_list("case_id", flat=True)
    return request.app.get_success(data_list)


async def get_report_step_list(request: Request, form: schema.GetReportStepListForm = Depends()):
    models = ModelSelector(request.app.test_type)
    step_list = await models.report_step.get_resport_step_list(form.report_case_id, form.get_summary)
    return request.app.get_success(step_list)


async def get_report_step(request: Request, form: schema.GetReportStepForm = Depends()):
    models = ModelSelector(request.app.test_type)
    data = await models.report_step.validate_is_exist("数据不存在", id=form.id)
    return request.app.get_success(data)


async def change_report_step_status(request: Request, form: schema.ChangeReportStepStatus):
    models = ModelSelector(request.app.test_type)
    await models.report_step.update_status(form.report_id, form.report_case_id, form.report_step_id, form.status)
    return request.app.put_success()


async def get_report_step_img(request: Request, form: schema.GetReportStepImgForm = Depends()):
    data = FileUtil.get_report_step_img(form.report_id, form.report_step_id, form.img_type, request.app.test_type)
    return request.app.get_success({"data": data, "total": 1 if data else 0})


async def get_report_status(request: Request, form: schema.GetReportStatusForm = Depends()):
    models = ModelSelector(request.app.test_type)
    data = await models.report.select_is_all_status_by_batch_id(form.batch_id, [form.process, form.status])
    return request.app.get_success(data)


async def get_report_show_id(request: Request, form: schema.GetReportShowIdForm = Depends()):
    models = ModelSelector(request.app.test_type)
    data = await models.report.select_show_report_id(form.batch_id)
    return request.app.get_success(data)


async def report_clear(request: Request, background_tasks: BackgroundTasks):
    # 清除报告数据比较耗时，用后台任务机制
    models = ModelSelector(request.app.test_type)
    background_tasks.add_task(models.report.clear_case_and_step, models.report_case, models.report_step)
    return request.app.success("触发清除成功")


async def get_report_detail(request: Request, form: schema.GetReportForm = Depends()):
    models = ModelSelector(request.app.test_type)
    report = await models.report.validate_is_exist("报告不存在", id=form.id)
    return request.app.get_success(report)


async def delete_report(request: Request, form: schema.DeleteReportForm):
    models = ModelSelector(request.app.test_type)
    if form.is_admin(request.state.user.api_permissions):  # 管理员，全都可以删
        id_list = await models.report.filter(id__in=form.id_list).all().values("id")
    else:  # 非管理员，触发方式为 pipeline 和 cron的，不给删
        id_list = await models.report.filter(
            id__in=form.id_list, trigger_type__not_in=['pipeline', 'cron']).all().values("id")
    report_id_list = [data["id"] for data in id_list]
    await models.report.filter(id__in=report_id_list).delete()
    FileUtil.delete_report_img_by_report_id(report_id_list, request.app.test_type)
    return request.app.delete_success()
