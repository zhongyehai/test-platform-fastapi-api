from fastapi import Request, BackgroundTasks, Depends

from app.schemas.enums import ApiCaseSuiteTypeEnum
from ...models.autotest.model_factory import ApiReport, ApiReportCase, ApiReportStep, AppReport, AppReportCase, \
    AppReportStep, UiReport, UiReportCase, UiReportStep, ApiMsg, ApiCase, ApiStep, ApiCaseSuite, \
    AppCaseSuite, UiCaseSuite
from ...schemas.autotest import reprot as schema
from utils.util.file_util import FileUtil


async def get_report_list(request: Request, form: schema.FindReportForm = Depends()):
    model = ApiReport if request.app.test_type == "api" else AppReport if request.app.test_type == "app" else UiReport
    get_filed = model.get_simple_filed_list()
    if form.detail:
        get_filed.extend([
            "create_time", "trigger_type", "env", "is_passed", "process", "status", "create_user", "project_id",
            "trigger_id", "run_type"
        ])

    query_data = await form.make_pagination(model, get_filed=get_filed)
    return request.app.get_success(data=query_data)


async def save_report_as_case(request: Request, form: schema.GetReportForm = Depends()):
    report_step = await ApiReportStep.filter(report_id=form.id).values("element_id", "name")
    if not report_step and not report_step.get("element_id"):
        ValueError("数据不存在")

    api = await ApiMsg.filter(id=report_step["element_id"]).first()
    case_suite = await ApiCaseSuite.filter(project_id=api.project_id, suite_type=ApiCaseSuiteTypeEnum.API).first()
    case = await ApiCase.model_create({
        "name": report_step["name"],
        "desc": report_step["name"],
        "suite_id": case_suite.id
    }, request.state.user)
    await ApiStep.model_create({
        "name": report_step["name"],
        "case_id": case.id,
        "api_id": api.id,
        **dict(api)
    }, request.state.user)
    return request.app.post_success()


async def get_report_suite_list(request: Request, form: schema.GetReportCaseSuiteListForm = Depends()):
    suite_model, report_case_model, report_step_model = ApiCaseSuite, ApiReportCase, ApiReportStep
    if request.app.test_type == "app":
        suite_model, report_case_model, report_step_model = AppCaseSuite, AppReportCase, AppReportStep
    elif request.app.test_type == "ui":
        suite_model, report_case_model, report_step_model = UiCaseSuite, UiReportCase, UiReportStep

    suite_and_case_list = await report_case_model.get_resport_suite_and_case_list(
        form.report_id, suite_model, report_step_model)
    return request.app.get_success(suite_and_case_list)


async def get_report_case_list(request: Request, form: schema.GetReportCaseListForm = Depends()):
    model = ApiReportCase if request.app.test_type == "api" else AppReportCase if request.app.test_type == "app" else UiReportCase
    case_list = await model.get_resport_case_list(form.report_id, form.get_summary)
    return request.app.get_success(case_list)


async def get_report_case(request: Request, form: schema.GetReportCaseForm = Depends()):
    model = ApiReportCase if request.app.test_type == "api" else AppReportCase if request.app.test_type == "app" else UiReportCase
    data = await model.validate_is_exist("数据不存在", id=form.id)
    return request.app.get_success(data)


async def get_report_case_failed_list(request: Request, form: schema.GetReportForm = Depends()):
    model = ApiReportCase if request.app.test_type == "api" else AppReportCase if request.app.test_type == "app" else UiReportCase
    case_list = await model.filter(report_id=form.id, result__not='success').all().values("case_id")
    return request.app.get_success([data["case_id"] for data in case_list])


async def get_report_step_list(request: Request, form: schema.GetReportStepListForm = Depends()):
    model = ApiReportStep if request.app.test_type == "api" else AppReportStep if request.app.test_type == "app" else UiReportStep
    step_list = await model.get_resport_step_list(form.report_case_id, form.get_summary)
    return request.app.get_success(step_list)


async def get_report_step(request: Request, form: schema.GetReportStepForm = Depends()):
    model = ApiReportStep if request.app.test_type == "api" else AppReportStep if request.app.test_type == "app" else UiReportStep
    data = await model.validate_is_exist("数据不存在", id=form.id)
    return request.app.get_success(data)


async def change_report_step_status(request: Request, form: schema.ChangeReportStepStatus):
    model = ApiReportStep if request.app.test_type == "api" else AppReportStep if request.app.test_type == "app" else UiReportStep
    await model.update_status(form.report_id, form.report_case_id, form.report_step_id, form.status)
    return request.app.put_success()


async def get_report_step_img(request: Request, form: schema.GetReportStepImgForm = Depends()):
    data = FileUtil.get_report_step_img(form.report_id, form.report_step_id, form.img_type, request.app.test_type)
    return request.app.get_success({"data": data, "total": 1 if data else 0})


async def get_report_status(request: Request, form: schema.GetReportStatusForm = Depends()):
    model = ApiReport if request.app.test_type == "api" else AppReport if request.app.test_type == "app" else UiReport
    data = await model.select_is_all_status_by_batch_id(form.batch_id, [form.process, form.status])
    return request.app.get_success(data)


async def get_report_show_id(request: Request, form: schema.GetReportShowIdForm = Depends()):
    model = ApiReport if request.app.test_type == "api" else AppReport if request.app.test_type == "app" else UiReport
    data = await model.select_show_report_id(form.batch_id)
    return request.app.get_success(data)


async def report_clear(request: Request, background_tasks: BackgroundTasks):
    # 清除报告数据比较耗时，用后台任务机制
    report_model, report_case_model, report_step_model = ApiReport, ApiReportCase, ApiReportStep
    if request.app.test_type == "app":
        report_model, report_case_model, report_step_model = AppReport, AppReportCase, AppReportStep
    elif request.app.test_type == "ui":
        report_model, report_case_model, report_step_model = UiReport, UiReportCase, UiReportStep

    background_tasks.add_task(report_model.clear_case_and_step, report_case_model, report_step_model)
    return request.app.success("触发清除成功")


async def get_report_detail(request: Request, form: schema.GetReportForm = Depends()):
    model = ApiReport if request.app.test_type == "api" else AppReport if request.app.test_type == "app" else UiReport
    report = await model.validate_is_exist("报告不存在", id=form.id)
    return request.app.get_success(report)


async def delete_report(request: Request, form: schema.DeleteReportForm):
    model = ApiReport if request.app.test_type == "api" else AppReport if request.app.test_type == "app" else UiReport
    if form.is_admin(request.state.user.api_permissions):  # 管理员，全都可以删
        id_list = await model.filter(id__in=form.id_list).all().values("id")
    else:  # 非管理员，触发方式为 pipeline 和 cron的，不给删
        id_list = await model.filter(
            id__in=form.id_list, trigger_type__not_in=['pipeline', 'cron']).all().values("id")
    report_id_list = [data["id"] for data in id_list]
    await model.filter(id__in=report_id_list).delete()
    FileUtil.delete_report_img_by_report_id(report_id_list, request.app.test_type)
    return request.app.delete_success()
