# -*- coding: utf-8 -*-
from typing import Optional
from pydantic import Field
from fastapi import Request

from ...baseForm import BaseForm, PaginationForm
from ..model_factory import Permission, PermissionPydantic, RolePermissions, RolePermissionsPydantic


class GetPermissionForm(BaseForm):
    """ 获取具体权限 """
    id: int = Field(..., title="权限id")

    async def validate_permission_id_is_exist(self):
        """ 数据值校验 """
        return await self.validate_id_is_exist(self.id, Permission, msg="权限不存在")

    async def validate_request(self, request: Request, *args, **kwargs):
        """ 数据值校验 """
        return await self.validate_permission_id_is_exist()


class CreatePermissionForm(BaseForm):
    """ 创建权限的验证 """
    name: str = Field(..., title="权限名", min_length=2, max_length=Permission.filed_max_length("name"))
    desc: Optional[str] = Field(title="备注", min_length=2, max_length=Permission.filed_max_length("desc"))
    create_user: Optional[int] = Field(title="创建人")
    source_addr: str = Field(..., title="权限地址", min_length=2, max_length=Permission.filed_max_length("source_addr"))
    source_type: str = Field("front", title="权限类型")
    source_class: str = Field("menu", title="权限分类")

    def validate_length(self):
        """ 数据长度校验 """
        self.validate_is_true(len(self.name) < Permission.filed_max_length("name"), msg="权限名长度超长")
        if self.desc:
            self.validate_is_true(len(self.desc) < Permission.filed_max_length("desc"), msg="备注长度超长")
        self.validate_is_true(
            len(self.source_addr) < Permission.filed_max_length("source_addr"), msg="权限地址长度超长")

    async def validate_request(self, request: Request, *args, **kwargs):
        """ 数据值校验 """
        self.validate_length()
        await self.validate_data_is_not_exist(f"权限名 {self.name} 已存在", Permission, name=self.name)


class FindPermissionForm(PaginationForm):
    """ 查找权限参数校验 """
    name: Optional[str] = Field(title="权限名")
    source_addr: Optional[str] = Field(title="权限地址")
    source_type: Optional[str] = Field(title="权限类型")

    def get_query_filter(self, *args, **kwargs):
        """ 查询条件 """
        filter_dict = {}
        if self.name:
            filter_dict["name__icontains"] = self.name
        if self.source_addr:
            filter_dict["source_addr__icontains"] = self.source_addr
        if self.source_type:
            filter_dict["source_type"] = self.source_type
        return filter_dict


class DeletePermissionForm(GetPermissionForm):
    """ 删除权限 """

    async def validate_request(self, request: Request, *args, **kwargs):
        """ 数据值校验 """
        permission = await self.validate_permission_id_is_exist()
        await self.validate_data_is_not_exist(
            "权限已被角色引用，请先解除引用", RolePermissions, permission_id=self.id)
        return permission


class EditPermissionForm(GetPermissionForm, CreatePermissionForm):
    """ 编辑权限的校验 """

    async def validate_request(self, request: Request, *args, **kwargs):
        """ 数据值校验 """
        self.validate_length()
        permission = await self.validate_permission_id_is_exist()
        await self.validate_data_is_not_repeat(f"权限名 {self.name} 已存在", Permission, request.data.id, name=self.name)
        return permission
