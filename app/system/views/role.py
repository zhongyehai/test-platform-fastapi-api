# -*- coding: utf-8 -*-
from typing import List
from fastapi import Request

from app.system.routers import system_router
from app.system.forms.role import FindRoleForm, GetRoleForm, CreateRoleForm, EditRoleForm, DeleteRoleForm
from app.system.model_factory import Role, RolePydantic, RolePermissions, RolePermissionsPydantic, User


@system_router.permission_post("/role/list", response_model=List[RolePydantic], summary="获取角色列表")
async def get_role_list(form: FindRoleForm, request: Request):
    await form.validate_request(request)
    query_data = await form.make_pagination(Role, role_id=request.app.role_id)
    return request.app.get_success(data=query_data)


@system_router.admin_post("/role/detail", summary="获取角色详情")
async def get_role_detail(form: GetRoleForm, request: Request):
    role = await form.validate_request(request)
    permissions = await User.get_role_permissions([form.id])
    return request.app.get_success(data={"data": role, **permissions})


@system_router.admin_post("/role", summary="新增角色")
async def add_role(form: CreateRoleForm, request: Request):
    await form.validate_request(request)
    data = form.dict()
    front_permission, api_permission = data.pop("front_permission"), data.pop("api_permission")
    role = await Role.model_create(data, request.state.user)
    await role.insert_role_permissions([*front_permission, *api_permission])
    return request.app.post_success()


@system_router.admin_put("/role", summary="修改角色")
async def change_role(form: EditRoleForm, request: Request):
    role = await form.validate_request(request)
    data = form.dict()
    front_permission, api_permission = data.pop("front_permission"), data.pop("api_permission")
    await role.model_update(data, request.state.user)
    await role.update_role_permissions([*front_permission, *api_permission])
    return request.app.put_success()


@system_router.admin_delete("/role", summary="删除角色")
async def delete_role(form: DeleteRoleForm, request: Request):
    role = await form.validate_request(request)
    await role.delete_role_permissions()
    await role.model_delete()
    return request.app.delete_success()
