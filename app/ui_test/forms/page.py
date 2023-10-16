from typing import Optional, List
from pydantic import Field

from ...baseForm import BaseForm, PaginationForm, AddCaseDataForm
from ..model_factory import WebUiProject as Project, WebUiModule as Module, WebUiPage as Page, WebUiElement as Element


class PageListForm(PaginationForm):
    """ 查询页面信息 """
    module_id: int = Field(..., title="模块id")
    name: Optional[str] = Field(title="模块名")

    def get_query_filter(self, *args, **kwargs):
        """ 查询条件 """
        filter_dict = {"module_id": self.module_id}
        if self.name:
            filter_dict["name__icontains"] = self.name
        return filter_dict


class GetPageForm(BaseForm):
    """ 获取页面 """
    id: int = Field(..., title="页面id")

    async def validate_page_is_exist(self):
        return await self.validate_data_is_exist("页面不存在", Page, id=self.id)

    async def validate_request(self, *args, **kwargs):
        return await self.validate_page_is_exist()


class DeletePageForm(GetPageForm):
    """ 删除页面 """

    async def validate_request(self, *args, **kwargs):
        page = await self.validate_page_is_exist()
        await self.validate_data_is_not_exist("当前页面下有元素，请先删除元素，再删除页面", Element, page_id=self.id)
        return page


class AddPageForm(BaseForm):
    """ 添加页面信息的校验 """
    project_id: int = Field(..., title="项目id")
    module_id: int = Field(..., title="模块id")
    page_list: List[AddCaseDataForm] = Field(..., title="页面list")

    async def validate_request(self, *args, **kwargs):
        await self.validate_data_is_exist("项目不存在", Project, id=self.project_id)
        await self.validate_data_is_exist("模块不存在", Module, id=self.module_id)

        page_list, name_list = [], []
        for index, page in enumerate(self.page_list):
            self.validate_is_true(f'第【{index + 1}】行，页面名必传', page.name)
            if page.name in name_list:
                raise ValueError(f'第【{index + 1}】行，与第【{name_list.index(page.name) + 1}】行，页面名重复')

            await self.validate_data_is_not_exist(
                f"当前模块下，名为【{page.name}】的页面已存在", Page, name=page.name, module_id=self.module_id)

            name_list.append(page.name)
            page_list.append({"project_id": self.project_id, "module_id": self.module_id, **page.dict()})
        return page_list


class EditPageForm(GetPageForm):
    """ 修改页面信息 """
    module_id: int = Field(..., title="模块id")
    id: int = Field(..., title="页面id")
    name: str = Field(..., title="页面名")
    desc: Optional[str] = Field(title="描述")
    addr: Optional[str] = Field(title="页面地址")

    async def validate_request(self, *args, **kwargs):
        page = await self.validate_data_is_exist("页面不存在", Page, id=self.id)
        await self.validate_data_is_not_repeat(
            f"页面名【{self.name}】已存在", Page, self.id, name=self.name, module_id=self.module_id)
        return page
