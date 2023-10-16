# -*- coding: utf-8 -*-
from typing import List
from fastapi import Request

from ..routers import config_router
from app.config.model_factory import ConfigType, ConfigPydantic
from app.config.forms.config import GetConfigTypeListForm, GetConfigTypeForm, PutConfigTypeForm, PostConfigTypeForm, \
    DeleteConfigTypeForm


@config_router.login_post("/type/list", response_model=List[ConfigPydantic], summary="获取配置类型列表")
async def get_config_type_list(form: GetConfigTypeListForm, request: Request):
    query_data = await form.make_pagination(ConfigType)
    return request.app.get_success(data=query_data)


@config_router.login_post("/type/detail", summary="获取配置类型详情")
async def get_config_type_detail(form: GetConfigTypeForm, request: Request):
    config_type = await form.validate_request(request)
    return request.app.get_success(data=config_type)


@config_router.login_post("/type", summary="新增配置类型")
async def add_config_type(form: PostConfigTypeForm, request: Request):
    await form.validate_request(request)
    await ConfigType.model_create(form.dict(), request.state.user)
    return request.app.post_success()


@config_router.admin_put("/type", summary="修改配置类型")
async def change_config_type(form: PutConfigTypeForm, request: Request):
    config_type = await form.validate_request(request)
    await config_type.model_update(form.dict(), request.state.user)
    return request.app.put_success()


@config_router.admin_delete("/type", summary="删除配置类型")
async def delete_config_type(form: DeleteConfigTypeForm, request: Request):
    config_type = await form.validate_request(request)
    await config_type.model_delete()
    return request.app.delete_success()
