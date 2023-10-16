from typing import Optional
from pydantic import Field
from fastapi import Request

from ...baseForm import BaseForm, PaginationForm
from ..model_factory import ApiCase as Case, ApiProject as Project, ApiCaseSuite as CaseSuite
from ...enums import ApiCaseSuiteTypeEnum


class FindCaseSuite(PaginationForm):
    """ 查找用例集合 """
    name: Optional[str] = Field(title="用例集名")
    suite_type: Optional[list] = Field(title="用例集类型")
    project_id: int = Field(..., title="服务id")

    def get_query_filter(self, *args, **kwargs):
        """ 查询条件 """
        filter_dict = {"project_id": self.project_id}
        if self.name:
            filter_dict["name__icontains"] = self.name
        if self.suite_type:
            filter_dict["suite_type__in"] = self.suite_type
        return filter_dict


class GetCaseSuiteForm(BaseForm):
    """ 获取用例集信息 """
    id: int = Field(..., title="用例集id")

    async def validate_suite_is_exist(self):
        return await self.validate_data_is_exist("用例集不存在", CaseSuite, id=self.id)

    async def validate_request(self, *args, **kwargs):
        return await self.validate_suite_is_exist()


class DeleteCaseSuiteForm(GetCaseSuiteForm):
    """ 删除用例集 """

    async def validate_request(self, *args, **kwargs):
        suite = await self.validate_suite_is_exist()
        await self.validate_data_is_not_exist("请先删除当前用例集的子用例集", CaseSuite, parent=self.id)
        await self.validate_data_is_not_exist("请先删除当前用例集下的用例", Case, suite_id=self.id)
        return suite


class AddCaseSuiteForm(BaseForm):
    """ 添加用例集的校验 """
    project_id: int = Field(..., title="服务id")
    name: str = Field(..., title="用例集名称")
    suite_type: ApiCaseSuiteTypeEnum = Field(
        ..., title="用例集类型", description="base: 基础用例集，api: 单接口用例集，process: 流程用例集，assist: 造数据用例集")
    parent: Optional[int] = Field(title="父用例集id")

    async def validate_project_is_exist(self):
        return await self.validate_data_is_exist("服务不存在", Project, id=self.project_id)

    async def validate_request(self, *args, **kwargs):
        await self.validate_project_is_exist()
        await self.validate_data_is_not_exist(
            f"当前层级下，用例集名字【{self.name}】已存在", CaseSuite, project_id=self.project_id, name=self.name,
            parent=self.parent)


class EditCaseSuiteForm(GetCaseSuiteForm, AddCaseSuiteForm):
    """ 编辑用例集 """

    async def validate_request(self, request: Request, *args, **kwargs):
        suite = await self.validate_suite_is_exist()
        await self.validate_project_is_exist()
        await self.validate_data_is_not_repeat(
            f"当前层级下，用例集名字【{self.name}】已存在",
            CaseSuite, self.id, project_id=self.project_id, name=self.name, parent=self.parent)

        # 判断是否修改了用例集类型
        request.is_update_suite_type = False
        if self.parent is None and self.suite_type != suite.suite_type:
            request.is_update_suite_type = True

        return suite


class RunCaseSuiteForm(GetCaseSuiteForm):
    """ 运行用例集 """
    is_async: int = Field(default=0, title="执行模式")
    env_list: list = Field(default=0, title="运行环境")

    async def validate_request(self, *args, **kwargs):
        suite = await self.validate_suite_is_exist()
        await self.validate_data_is_exist("用例集下没有用例", Case, suite_id=self.id)
        return suite
