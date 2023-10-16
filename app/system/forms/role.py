# -*- coding: utf-8 -*-
from typing import Optional
from pydantic import Field
from fastapi import Request
from tortoise.query_utils import Prefetch

from ..models.user import User, Permission, RolePermissions
from ...baseForm import BaseForm, PaginationForm
from ..model_factory import Role, RolePydantic, UserRoles, UserRolesPydantic


class GetRoleForm(BaseForm):
    """ 获取具体角色 """
    id: int = Field(..., title="角色id")

    async def validate_role_id_is_exist(self):
        """ 数据值校验 """
        return await self.validate_id_is_exist(self.id, Role, msg="角色不存在")

    async def validate_request(self, request: Request, *args, **kwargs):
        """ 数据值校验 """
        return await self.validate_role_id_is_exist()


class CreateRoleForm(BaseForm):
    """ 创建角色的验证 """
    name: str = Field(..., title="角色名", min_length=2, max_length=Role.filed_max_length("name"))
    desc: str = Field(..., title="备注", min_length=2, max_length=Role.filed_max_length("desc"))
    extend_role: list = Field([], title="继承角色")
    api_permission: list = Field([], title="后端权限")
    front_permission: list = Field([], title="前端权限")

    def validate_length(self):
        """ 数据长度校验 """
        self.validate_is_true(len(self.name) < Role.filed_max_length("name"), msg="角色名长度超长")
        self.validate_is_true(len(self.desc) < Role.filed_max_length("desc"), msg="备注长度超长")

    async def validate_request(self, *args, **kwargs):
        """ 数据值校验 """
        self.validate_length()
        await self.validate_data_is_not_exist(f"角色名 {self.name} 已存在", Role, name=self.name)


class FindRoleForm(PaginationForm):
    """ 查找角色参数校验 """
    name: Optional[str] = Field(title="角色名")
    role_id: Optional[int] = Field(title="权角色id")

    async def validate_request(self, request: Request, *args, **kwargs):
        """ 如果不是管理员，则不返回管理员角色 """
        request.app.role_id = []
        if User.is_not_admin(request.state.user.api_permissions):
            # 管理员权限
            admin_permission = [p.id for p in await Permission.filter(source_addr="admin").all()]
            # 没有管理员权限的角色
            not_admin_roles = await RolePermissions.filter(permission_id__not_in=admin_permission).distinct().values("role_id")
            request.app.role_id = [role["role_id"] for role in not_admin_roles]

    def get_query_filter(self, *args, **kwargs):
        """ 查询条件 """
        role_id, filter_dict = kwargs.get("role_id"), {}
        if role_id:
            filter_dict["id__in"] = role_id
        if self.name:
            filter_dict["name__icontains"] = self.name
        return filter_dict


class DeleteRoleForm(GetRoleForm):
    """ 删除角色 """

    async def validate_request(self, request: Request, *args, **kwargs):
        """ 数据值校验 """
        role = await self.validate_role_id_is_exist()
        await self.validate_data_is_not_exist("角色已被用户引用，请先解除引用", UserRoles, role_id=self.id)
        return role


class EditRoleForm(GetRoleForm, CreateRoleForm):
    """ 编辑角色的校验 """

    async def validate_request(self, request: Request, *args, **kwargs):
        """ 数据值校验 """
        self.validate_length()
        role = await self.validate_role_id_is_exist()
        await self.validate_data_is_not_repeat(f"角色名 {self.name} 已存在", Role, role.id, name=self.name)
        return role
