from typing import List
from fastapi import Request

from ..routers import config_router
from app.config.model_factory import Config, ConfigPydantic
from ..forms.config import FindConfigForm, GetConfigForm, PostConfigForm, PutConfigForm, DeleteConfigForm, \
    GetSkipIfConfigForm, GetFindElementByForm


@config_router.login_post("/config/list", summary="获取配置列表")
async def get_config_list(form: FindConfigForm, request: Request):
    query_data = await form.make_pagination(Config)
    return request.app.get_success(data=query_data)


@config_router.post("/config/by/code", summary="获取配置")
async def get_config_by_code(form: GetConfigForm, request: Request):
    config = await form.validate_request(request)
    return request.app.get_success(config)


@config_router.post("/config/skip/if", summary="获取跳过类型配置")
async def get_config_skip_if(form: GetSkipIfConfigForm, request: Request):
    conf = form.validate_request(request)
    return request.app.get_success(data=conf)


@config_router.post("/config/find/element", summary="获取定位方式数据源")
async def get_config_find_element(form: GetFindElementByForm, request: Request):
    conf = form.validate_request(request)
    return request.app.get_success(data=conf)


@config_router.login_post("/config/detail", summary="获取配置详情")
async def get_config_detail(form: GetConfigForm, request: Request):
    config = await form.validate_request(request)
    return request.app.get_success(config)


@config_router.login_post("/config", summary="新增配置")
async def add_config(form: PostConfigForm, request: Request):
    await form.validate_request(request)
    await Config.model_create(form.dict(), request.state.user)
    return request.app.post_success()


@config_router.login_put("/config", summary="修改配置")
async def change_config(form: PutConfigForm, request: Request):
    config = await form.validate_request(request)
    await config.model_update(form.dict(), request.state.user)
    return request.app.put_success()


@config_router.login_delete("/config", summary="删除配置")
async def delete_config(form: DeleteConfigForm, request: Request):
    config = await form.validate_request(request)
    await config.model_delete()
    return request.app.delete_success()
