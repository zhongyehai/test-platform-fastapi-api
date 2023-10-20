from typing import List
from fastapi import Request, BackgroundTasks

from ..routers import ui_test
from ...baseForm import ChangeSortForm
from ..model_factory import WebUiCasePydantic as CasePydantic, WebUiProject as Project, WebUiCase as Case, \
    WebUiStep as Step, WebUiReport as Report, WebUiCaseSuite as CaseSuite
from ..forms.case import AddCaseForm, EditCaseForm, FindCaseForm, DeleteCaseForm, GetCaseForm, RunCaseForm, \
    CopyCaseStepForm, ChangeCaseStatusForm, GetAssistCaseForm, GetCaseNameForm
from app.busines import RunCaseBusiness, CaseBusiness
from utils.client.run_ui_test import RunCase


@ui_test.login_post("/case/list", response_model=List[CasePydantic], summary="获取用例列表")
async def ui_get_case_list(form: FindCaseForm, request: Request):
    query_data = await form.make_pagination(Case, user=request.state.user)
    if form.has_step:
        total, data_list = query_data["total"], await Step.set_has_step_for_case(query_data["data"])
        return request.app.get_success(data={"total": total, "data": data_list})
    return request.app.get_success(data=query_data)


@ui_test.login_put("/case/sort", summary="用例排序")
async def ui_change_case_sort(form: ChangeSortForm, request: Request):
    await Case.change_sort(**form.dict(exclude_unset=True))
    return request.app.put_success()


@ui_test.login_post("/case/assist/list", summary="获取造数用例集的用例list")
async def ui_get_get_case_list(form: GetAssistCaseForm, request: Request):
    case_list = await CaseSuite.get_make_data_case(form.project_id, Case)
    return request.app.get_success(data={"total": len(case_list), "data": case_list})


@ui_test.login_post("/case/name", summary="根据用例id获取用例名")
async def ui_get_case_name(form: GetCaseNameForm, request: Request):
    case_list = await Case.filter(id__in=form.case_list).all().values("id", "name")
    data = [{"id": case["id"], "name": case["name"]} for case in case_list]
    return request.app.get_success(data=data)


@ui_test.login_post("/case/project", summary="获取用例属于哪个用例集、哪个用例")
async def ui_get_case_of_project(form: GetCaseForm, request: Request):
    case = await Case.filter(id=form.id).first()
    suite = await CaseSuite.filter(id=case.suite_id).first()
    project = await Project.filter(id=suite.project_id).first()
    return request.app.get_success(data={"case": case, "suite": suite, "project": project})


@ui_test.login_put("/case/status", summary="修改用例状态（是否执行）")
async def ui_change_case_status(form: ChangeCaseStatusForm, request: Request):
    await Case.filter(id__in=form.id_list).update(status=form.status.value)
    return request.app.put_success()


@ui_test.login_post("/case/copy", summary="复制用例")
async def ui_copy_case(form: GetCaseForm, request: Request):
    case = await form.validate_request()
    new_case = await CaseBusiness.copy(case, Case, Step, request.state.user)
    return request.app.success("复制成功", data=new_case)


@ui_test.login_post("/case/from", summary="获取用例的归属")
async def ui_case_from(form: GetCaseForm, request: Request):
    case = await form.validate_request()
    from_path = await CaseBusiness.get_quote_case_from(case, Project, CaseSuite)
    return request.app.get_success(data=from_path)


@ui_test.login_post("/case/copy/step", summary="复制指定步骤到当前用例下")
async def ui_case_copy_step(form: CopyCaseStepForm, request: Request):
    await form.validate_request()
    step_list = await CaseBusiness.copy_case_all_step_to_current_case(form, Step, Case, request.state.user)
    await Case.merge_variables(form.from_case, form.to_case)
    return request.app.success("步骤复制成功，自定义变量已合并至当前用例", data=step_list)


# @ui_test.login_post("/case/pull/step", summary="复制指定用例的步骤到当前用例下")
# async def ui_get_ui_list(form: PullCaseStepForm, request: Request):
#     await form.validate_request()
#     await CaseBusiness.copy_step_to_current_case(form, Step)
#     return request.app.success("步骤复制成功，自定义变量已合并至当前用例", data=step_list)


@ui_test.login_post("/case/detail", summary="获取用例详情")
async def ui_get_case_detail(form: GetCaseForm, request: Request):
    case = await form.validate_request(request)
    return request.app.get_success(data=case)


@ui_test.login_post("/case", summary="新增用例")
async def ui_add_case(form: AddCaseForm, request: Request):
    case_list = await form.validate_request()
    if len(form.case_list) == 1:
        return request.app.post_success(await Case.model_create(case_list[0], request.state.user))
    await Case.batch_insert(case_list, request.state.user)
    return request.app.post_success()


@ui_test.login_put("/case", summary="修改用例")
async def ui_change_case(form: EditCaseForm, request: Request):
    case = await form.validate_request(request)
    await case.model_update(form.dict(), request.state.user)
    return request.app.put_success()


@ui_test.login_delete("/case", summary="删除用例")
async def ui_delete_case(form: DeleteCaseForm, request: Request):
    case = await form.validate_request(request)
    await case.delete_case(Step)
    return request.app.delete_success()


@ui_test.login_post("/case/run", summary="运行测试用例")
async def ui_run_case(form: RunCaseForm, request: Request, background_tasks: BackgroundTasks):
    case_list = await form.validate_request(request)
    case_suite = await CaseSuite.filter(id=case_list[0].suite_id).first()
    batch_id = Report.get_batch_id(request.state.user.id)
    for env_code in form.env_list:
        report_id = await RunCaseBusiness.run(
            batch_id=batch_id,
            env_code=env_code,
            browser=form.browser,
            is_async=form.is_async,
            project_id=case_suite.project_id,
            temp_variables=form.temp_variables,
            report_name=case_list[0].name,
            task_type="case",
            report_model=Report,
            case_id_list=form.case_id_list,
            run_type="webUi",
            runner=RunCase,
            create_user=request.state.user.id
        )
    return request.app.trigger_success({
            "batch_id": batch_id,
            "report_id": report_id if len(form.env_list) == 1 else None
        })
