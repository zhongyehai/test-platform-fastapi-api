from typing import Optional
from pydantic import Field
from fastapi import Request

from ...baseForm import BaseForm, PaginationForm
from ..model_factory import AppUiProject as Project, AppUiModule as Module, AppUiPage as Page


class GetModuleTreeForm(BaseForm):
    project_id: int = Field(..., title="项目id")

    async def validate_project_is_exist(self):
        return await self.validate_data_is_exist("项目不存在", Project, id=self.project_id)

    async def validate_request(self, *args, **kwargs):
        await self.validate_project_is_exist()


class FindModuleForm(GetModuleTreeForm, PaginationForm):
    """ 查找模块 """
    name: Optional[str] = Field(title="模块名")

    def get_query_filter(self, *args, **kwargs):
        """ 查询条件 """
        filter_dict = {"project_id": self.project_id}
        if self.name:
            filter_dict["name__icontains"] = self.name
        return filter_dict


class AddModuleForm(GetModuleTreeForm):
    """ 添加模块的校验 """
    name: str = Field(..., title="模块名")
    parent: Optional[int] = Field(title="父级id")

    async def validate_request(self, request: Request, *args, **kwargs):
        await self.validate_project_is_exist()
        await self.validate_data_is_not_exist(
            f"当前层级中已存在名为【{self.name}】的模块", Module,
            project_id=self.project_id, name=self.name, parent=self.parent
        )


class GetModuleForm(BaseForm):
    """ 获取模块信息 """
    id: int = Field(..., title="模块id")

    async def validate_module_is_exist(self):
        return await self.validate_data_is_exist("模块不存在", Module, id=self.id)

    async def validate_request(self, request: Request, *args, **kwargs):
        return await self.validate_module_is_exist()


class DeleteModuleForm(GetModuleForm):
    """ 删除模块 """

    async def validate_request(self, request: Request, *args, **kwargs):
        module = await self.validate_module_is_exist()
        await self.validate_data_is_not_exist("请先删除模块下的页面", Page, module_id=module.id)
        await self.validate_data_is_not_exist("请先删除当前模块下的子模块", Module, parent=module.id)
        return module


class EditModuleForm(GetModuleForm, AddModuleForm):
    """ 修改模块的校验 """
    project_id: int = Field(..., title="项目id")

    async def validate_request(self, request: Request, *args, **kwargs):
        module = await self.validate_module_is_exist()
        await self.validate_data_is_not_repeat(
            f"当前层级中已存在名为【{self.name}】的模块", Module, self.id, project_id=self.project_id,
            name=self.name, parent=self.parent
        )
        return module
