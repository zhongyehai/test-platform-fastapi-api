# -*- coding: utf-8 -*-
from typing import List
from fastapi import Request

from ..routers import system_router
from app.system.model_factory import Permission, PermissionPydantic, RolePermissions, RolePermissionsPydantic
from app.system.forms.permission import FindPermissionForm, GetPermissionForm, CreatePermissionForm, \
    DeletePermissionForm, EditPermissionForm
from ...baseForm import ChangeSortForm


@system_router.admin_post("/permission/type", summary="获取权限类型")
async def get_permission_type(request: Request):
    return request.app.get_success(data={"api": '接口地址', "front": '前端地址'})


@system_router.post("/permission/list", response_model=List[PermissionPydantic], summary="获取权限列表")
async def get_permission_list(form: FindPermissionForm, request: Request):
    query_data = await form.make_pagination(Permission)
    return request.app.get_success(data=query_data)


@system_router.admin_put("/permission/sort", summary="修改排序")
async def change_permission_sort(form: ChangeSortForm, request: Request):
    await Permission.change_sort(**form.dict(exclude_unset=True))
    return request.app.put_success()


@system_router.admin_post("/permission/detail", summary="获取权限详情")
async def get_permission_detail(form: GetPermissionForm, request: Request):
    permission = await form.validate_request(request)
    return request.app.get_success(permission)


@system_router.admin_post("/permission", summary="新增权限")
async def add_permission(form: CreatePermissionForm, request: Request):
    await form.validate_request(request)
    await Permission.model_create(form.dict(), request.state.user)
    return request.app.post_success()


@system_router.admin_put("/permission", summary="修改权限")
async def change_permission(form: EditPermissionForm, request: Request):
    permission = await form.validate_request(request)
    await permission.model_update(form.dict(), request.state.user)
    return request.app.put_success()


@system_router.admin_delete("/permission", summary="删除权限")
async def remove_permission(form: DeletePermissionForm, request: Request):
    permission = await form.validate_request(request)
    await permission.model_delete()
    return request.app.delete_success()
