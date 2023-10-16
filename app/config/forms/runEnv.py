from typing import Optional
from pydantic import Field
from fastapi import Request

from ...baseForm import BaseForm, PaginationForm
from ..model_factory import RunEnv, BusinessLine


class GetRunEnvListForm(PaginationForm):
    """ 获取环境列表 """
    name: Optional[str] = Field(title="环境名")
    code: Optional[str] = Field(title="环境code")
    group: Optional[str] = Field(title="环境分组")
    create_user: Optional[str] = Field(title="创建者")

    def get_query_filter(self, *args, **kwargs):
        """ 查询条件 """
        user, filter_dict = kwargs.get("user"), {}
        if self.name:
            filter_dict["name__icontains"] = self.name
        if self.code:
            filter_dict["code__icontains"] = self.code
        if self.group:
            filter_dict["group__icontains"] = self.group
        if self.create_user:
            filter_dict["create_user"] = int(self.create_user)
        return filter_dict


class GetRunEnvForm(BaseForm):
    """ 获取环境表单校验 """
    id: int = Field(..., title="环境id")

    async def validate_run_env_id(self):
        return await self.validate_data_is_exist("环境不存在", RunEnv, id=self.id)

    async def validate_request(self, request: Request, *args, **kwargs):
        return await self.validate_run_env_id()


class DeleteRunEnvForm(GetRunEnvForm):
    """ 删除环境表单校验 """

    async def validate_request(self, request: Request, *args, **kwargs):
        return await self.validate_run_env_id()


class PostRunEnvForm(BaseForm):
    """ 新增环境表单校验 """
    name: str = Field(..., title="环境名", min_length=2, max_length=RunEnv.filed_max_length("name"))
    code: str = Field(..., title="环境code", min_length=2, max_length=RunEnv.filed_max_length("code"))
    group: str = Field(..., title="环境分组", min_length=2, max_length=RunEnv.filed_max_length("group"))
    desc: Optional[str] = Field(title="备注", max_length=RunEnv.filed_max_length("desc"))

    async def validate_request(self, request: Request, *args, **kwargs):
        await self.validate_data_is_not_exist('环境名已存在', RunEnv, name=self.name)
        await self.validate_data_is_not_exist('环境code已存在', RunEnv, code=self.code)


class PutRunEnvForm(GetRunEnvForm, PostRunEnvForm):
    """ 修改环境表单校验 """

    async def validate_request(self, request: Request, *args, **kwargs):
        env = await self.validate_run_env_id()
        await self.validate_data_is_not_repeat('环境名已存在', RunEnv, self.id, name=self.name)
        await self.validate_data_is_not_repeat('环境code已存在', RunEnv, self.id, code=self.code)
        return env


class GetEnvGroupForm(BaseForm):
    """ 获取环境分组 """

    env_list: list = Field(..., title="环境")
    business_list: list = Field(..., title="业务线")
    command: str = Field(..., title="操作类型")  # add、delete


class EnvToBusinessForm(BaseForm):
    """ 批量管理环境与业务线的关系 绑定/解除绑定 """

    env_list: list = Field(..., title="环境")
    business_list: list = Field(..., title="业务线")
    command: str = Field(..., title="操作类型")  # add、delete


class ChangeEnvSortForm(BaseForm):
    """ 权限排序校验 """
    id_list: list = Field(..., title="要排序的id列表")
    page_num: int = Field(1, title="页数")
    page_size: int = Field(10, title="页码")
