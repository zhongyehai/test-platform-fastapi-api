import os
from typing import List
from fastapi.responses import FileResponse
from fastapi import Request, UploadFile, File, Form

from ..routers import api_test
from ...busines import RunCaseBusiness, CaseSuiteBusiness
from ..model_factory import ApiCase as Case, ApiReport as Report, ApiCaseSuite as CaseSuite, \
    ApiCaseSuitePydantic as CaseSuitePydantic
from ..forms.suite import AddCaseSuiteForm, EditCaseSuiteForm, FindCaseSuite, GetCaseSuiteForm, \
    DeleteCaseSuiteForm, RunCaseSuiteForm
from utils.client.run_api_test import RunCase
from utils.util.file_util import STATIC_ADDRESS


@api_test.login_post("/suite/list", response_model=List[CaseSuitePydantic], summary="获取用例集列表")
async def api_get_suite_list(form: FindCaseSuite, request: Request):
    query_data = await form.make_pagination(CaseSuite, user=request.state.user)
    return request.app.get_success(data=query_data)


@api_test.login_post("/suite/template", summary="下载用例集导入模板")
async def api_get_suite_template(request: Request):
    return FileResponse(os.path.join(STATIC_ADDRESS, "用例集导入模板.xmind"))


@api_test.login_post("/suite/upload", summary="导入用例集")
async def api_upload_suite(request: Request, file: UploadFile = File(), project_id: str = Form()):
    if project_id is None:
        return request.app.fail("服务必传")
    if file and file.filename.endswith("xmind"):
        upload_res = await CaseSuiteBusiness.upload_case_suite(project_id, file, CaseSuite, Case)
        return request.app.success("导入完成", upload_res)
    return request.app.fail("文件格式错误")


@api_test.login_post("/suite/detail", summary="获取用例集详情")
async def api_get_suite_detail(form: GetCaseSuiteForm, request: Request):
    suite = await form.validate_request(request)
    return request.app.get_success(data=suite)


@api_test.login_post("/suite", summary="新增用例集")
async def api_add_suite(form: AddCaseSuiteForm, request: Request):
    await form.validate_request(request)
    suite = await CaseSuite.model_create(form.dict(), request.state.user)
    return request.app.post_success(suite)


@api_test.login_put("/suite", summary="修改用例集")
async def api_change_suite(form: EditCaseSuiteForm, request: Request):
    suite = await form.validate_request(request)
    await suite.model_update(form.dict(), request.state.user)
    suite.suite_type = form.suite_type
    await suite.update_children_suite_type()
    return request.app.put_success(form.dict())


@api_test.login_delete("/suite", summary="删除用例集")
async def api_delete_suite(form: DeleteCaseSuiteForm, request: Request):
    suite = await form.validate_request(request)
    await suite.model_delete()
    return request.app.delete_success()


@api_test.login_post("/suite/run", summary="运行用例集")
async def api_run_suite(form: RunCaseSuiteForm, request: Request):
    suite = await form.validate_request(request)
    case_id_list = await suite.get_run_case_id(Case)
    batch_id = Report.get_batch_id(request.state.user.id)
    for env_code in form.env_list:
        report_id = await RunCaseBusiness.run(
            batch_id=batch_id,
            env_code=env_code,
            is_async=form.is_async,
            project_id=suite.project_id,
            report_name=suite.name,
            task_type="suite",
            report_model=Report,
            trigger_id=form.id,
            case_id_list=case_id_list,
            create_user=request.state.user.id,
            run_type="api",
            runner=RunCase
        )

    return request.app.trigger_success({
            "batch_id": batch_id,
            "report_id": report_id if len(form.env_list) == 1 else None
        })
