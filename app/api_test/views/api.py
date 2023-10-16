# -*- coding: utf-8 -*-
import asyncio
import copy
import os.path

from typing import List
from fastapi import Request, UploadFile, File, Form
from fastapi.responses import FileResponse

from ..routers import api_test
from ...baseForm import ChangeSortForm
from ..model_factory import ApiModule as Module, ApiProject as Project, ApiReport as Report, ApiMsg as Api, \
    ApiMsgPydantic, ApiCase as Case, ApiCaseSuite as CaseSuite, ApiStep as Step
from ..forms.api import AddApiForm, EditApiForm, RunApiMsgForm, DeleteApiForm, ApiListForm, GetApiForm, \
    GetApiFromForm, ChangeLevel, ChangeStatus
from utils.util.file_util import STATIC_ADDRESS
from utils.parse.parse_excel import parse_file_content
from utils.client.run_api_test import RunApi


@api_test.login_post("/api/list", response_model=List[ApiMsgPydantic], summary="获取接口列表")
async def api_get_api_list(form: ApiListForm, request: Request):
    query_data = await form.make_pagination(Api, user=request.state.user)
    return request.app.get_success(data=query_data)


@api_test.login_put("/api/level", summary="修改接口等级")
async def api_change_api_level(form: ChangeLevel, request: Request):
    await Api.filter(id=form.id).update(level=form.level)
    return request.app.put_success()


@api_test.login_put("/api/status", summary="修改接口的废弃状态")
async def api_change_api_status(form: ChangeStatus, request: Request):
    await Api.filter(id=form.id).update(status=form.status)
    return request.app.put_success()


@api_test.login_post("/api/from", summary="获取接口的归属信息")
async def api_get_api_from(form: GetApiFromForm, request: Request):
    api_list = await form.validate_request()
    api_from_list = []
    for api in api_list:  # 多个接口存在同一个接口地址的情况
        project = await Project.filter(id=api.project_id).first()
        module_name = await Module.get_from_path(api.module_id)
        api_dict = dict(api)
        api_dict["from"] = f'【{project.name}_{module_name}_{api.name}】'
        api_from_list.append(api_dict)
    return request.app.get_success(data=api_from_list)


@api_test.login_post("/api/use", summary="查询哪些用例下的步骤引用了当前接口")
async def api_get_api_use(form: GetApiFromForm, request: Request):
    api_list = await form.validate_request()
    case_list, case_dict, project_dict = [], {}, {}  # 可能存在重复获取数据的请，获取到就存下来，一条数据只查一次库
    for api in api_list:  # 多个接口存在同一个接口地址的情况
        for step in await Step.filter(api_id=api.id).all():  # 存在一个接口在多个步骤调用的情况
            # 获取步骤所在的用例
            if step.case_id not in case_dict:
                case_dict[step.case_id] = await Case.filter(id=step.case_id).first()
            case = case_dict[step.case_id]

            # 获取用例所在的用例集
            suite = await CaseSuite.filter(id=case.suite_id).first()
            suite_from_path = await CaseSuite.get_from_path(suite.id)

            # 获取用例集所在的接口
            if suite.project_id not in project_dict:
                project_dict[suite.project_id] = await Project.filter(id=suite.project_id).first()
            project = project_dict[suite.project_id]

            case_dict = dict(case)
            case_dict["from"] = f'【{project.name if project else None}_{suite_from_path}_{case.name}_{step.name}】'
            case_list.append(copy.deepcopy(case_dict))
    return request.app.get_success(data=case_list)


@api_test.post("/api/template", summary="下载接口导入模板")
async def api_get_api_template(request: Request):
    return FileResponse(os.path.join(STATIC_ADDRESS, "接口导入模板.xls"))


@api_test.login_post("/api/upload", summary="从excel中导入接口")
async def upload_api(request: Request, file: UploadFile = File(), module_id: str = Form()):
    module = await Module.filter(id=module_id).first()
    if not module:
        return request.app.fail("模块不存在")
    if file and file.filename.endswith("xls"):
        # [{"请求类型": "get", "接口名称": "xx接口", "addr": "/api/v1/xxx"}]
        excel_data = parse_file_content(await file.read())
        api_list = []
        for api_data in excel_data:
            new_api = Api()
            for key, value in api_data.items():
                if hasattr(new_api, key):
                    setattr(new_api, key, value)
            new_api.method = api_data.get("method", "post").upper()
            new_api.project_id = module.project_id
            new_api.module_id = module.id
            new_api.create_user = request.state.user.id
            api_list.append(new_api)
        await Api.bulk_create(api_list)
        return request.app.success("接口导入成功")
    return request.app.fail("请上传后缀为xls的Excel文件")


@api_test.login_put("/api/sort", summary="修改接口的排序")
async def api_change_api_sort(form: ChangeSortForm, request: Request):
    await Api.change_sort(**form.dict(exclude_unset=True))
    return request.app.put_success()


@api_test.login_post("/api/detail", summary="获取接口详情")
async def api_get_api_detail(form: GetApiForm, request: Request):
    api = await form.validate_request()
    return request.app.get_success(api)


@api_test.login_post("/api", summary="新增接口")
async def add_api(form: AddApiForm, request: Request):
    await form.validate_request()
    await Api.model_create(form.dict(), request.state.user)
    return request.app.post_success()


@api_test.login_put("/api", summary="修改接口")
async def change_api(form: EditApiForm, request: Request):
    api = await form.validate_request()
    await api.model_update(form.dict(), request.state.user)
    return request.app.put_success()


@api_test.login_delete("/api", summary="删除接口")
async def delete_api(form: DeleteApiForm, request: Request):
    api = await form.validate_request()
    await api.model_delete()
    return request.app.delete_success()


@api_test.login_post("/api/run", summary="运行接口")
async def run_api(form: RunApiMsgForm, request: Request):
    run_api_list = await form.validate_request()
    batch_id = Report.get_batch_id(request.state.user.id)
    summary = Report.get_summary_template()
    for env_code in form.env_list:
        summary["env"]["code"], summary["env"]["name"] = env_code, env_code
        report = await Report.get_new_report(
            batch_id=batch_id,
            run_id=run_api_list[0].id,
            trigger_id=form.api_list,
            name=run_api_list[0].name,
            run_type="api",
            env=env_code,
            create_user=request.state.user.id,
            project_id=form.project_id,
            summary=summary
        )

        asyncio.create_task(RunApi(
            project_id=form.project_id, run_name=report.name, api_list=run_api_list, report=report, env_code=env_code
        ).parse_and_run())

    return request.app.trigger_success(data={"batch_id": batch_id})
