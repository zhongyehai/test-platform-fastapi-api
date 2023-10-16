from typing import List
from fastapi import Request

from ..routers import app_test
from ..model_factory import AppUiModule as Module, AppUiModulePydantic as ModulePydantic
from ..forms.module import AddModuleForm, EditModuleForm, FindModuleForm, DeleteModuleForm, GetModuleForm, \
    GetModuleTreeForm


@app_test.login_post("/module/list", response_model=List[ModulePydantic], summary="获取模块列表")
async def app_get_module_list(form: FindModuleForm, request: Request):
    query_data = await form.make_pagination(Module, user=request.state.user)
    return request.app.get_success(data=query_data)


@app_test.login_post("/module/tree", summary="获取服务下的模块树")
async def app_get_module_tree(form: GetModuleTreeForm, request: Request):
    await form.validate_request()
    module_list = await Module.filter(project_id=form.project_id).order_by("create_time").all()
    return request.app.get_success(data=module_list)


@app_test.login_post("/module/detail", summary="获取模块详情")
async def app_get_module_detail(form: GetModuleForm, request: Request):
    module = await form.validate_request(request)
    return request.app.get_success(module)


@app_test.login_post("/module", summary="新增模块")
async def app_add_module(form: AddModuleForm, request: Request):
    await form.validate_request(request)
    module = await Module.model_create(form.dict(), request.state.user)
    return request.app.post_success(data=module)


@app_test.login_put("/module", summary="修改模块")
async def app_change_module(form: EditModuleForm, request: Request):
    module = await form.validate_request(request)
    await module.model_update(form.dict(), request.state.user)
    return request.app.put_success(data=form.dict())


@app_test.login_delete("/module", summary="删除模块")
async def app_delete_module(form: DeleteModuleForm, request: Request):
    module = await form.validate_request(request)
    await module.model_delete()
    return request.app.delete_success()
