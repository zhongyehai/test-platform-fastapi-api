from typing import Optional, List
from pydantic import Field

from ...baseForm import BaseForm, PaginationForm, AddAppElementDataForm
from ..model_factory import AppUiProject as Project, AppUiModule as Module, AppUiPage as Page, AppUiElement as Element, \
    AppUiCaseSuite as CaseSuite, AppUiCase as Case, AppUiStep as Step
from ...busines import CaseBusiness


class ElementListForm(PaginationForm):
    """ 查询元素信息 """
    page_id: int = Field(..., title="页面id")
    name: Optional[str] = Field(title="元素名")

    def get_query_filter(self, *args, **kwargs):
        """ 查询条件 """
        filter_dict = {"page_id": self.page_id}
        if self.name:
            filter_dict["name__icontains"] = self.name
        return filter_dict


class GetElementForm(BaseForm):
    """ 获取元素 """
    id: int = Field(..., title="元素id")

    async def validate_element_is_exist(self):
        return await self.validate_data_is_exist("元素不存在", Element, id=self.id)

    async def validate_request(self, *args, **kwargs):
        return await self.validate_element_is_exist()


class DeleteElementForm(GetElementForm):
    """ 删除元素 """

    async def validate_request(self, *args, **kwargs):
        element = await self.validate_element_is_exist()
        step = await Step.filter(element_id=element.id).first()
        if step:
            case = await Case.filter(id=step.case_id).first()
            case_from = await CaseBusiness.get_quote_case_from(case, Project, CaseSuite)
            raise ValueError(f'步骤【{case_from}/{step.name}】已引用此元素，请先解除引用')
        return element


class AddElementForm(BaseForm):
    """ 添加元素信息的校验 """
    project_id: int = Field(..., title="项目id")
    module_id: int = Field(..., title="模块id")
    page_id: int = Field(..., title="页面id")
    element_list: List[AddAppElementDataForm] = Field(..., title="元素list")

    async def validate_request(self, *args, **kwargs):
        addr_lit, element_list = [], []
        await self.validate_data_is_exist("项目不存在", Project, id=self.project_id)
        await self.validate_data_is_exist("模块不存在", Module, id=self.module_id)
        await self.validate_data_is_exist("页面不存在", Page, id=self.page_id)

        name_list = []
        for index, element in enumerate(self.element_list):
            self.validate_is_true(f'第【{index + 1}】行，元素名必传', element.name)
            self.validate_is_true(f'第【{index + 1}】行，定位方式必传', element.by)
            self.validate_is_true(f'第【{index + 1}】行，元素表达式必传', element.element)
            if element.name in name_list:
                raise ValueError(f'第【{index + 1}】行，与第【{name_list.index(element.name) + 1}】行，元素名重复')

            await self.validate_data_is_not_exist(
                f"当前页面下，名为【{element.name}】的元素已存在", Element, name=element.name, page_id=self.page_id)

            if element.by == "url": addr_lit.append(element.element)
            name_list.append(element.name)
            element_list.append({
                "project_id": self.project_id, "module_id": self.module_id, "page_id": self.page_id, **element.dict()
            })

        # 如果元素是页面地址，则同步修改页面表里面对应的地址
        if len(addr_lit) > 0:
            await Page.filter(id=self.page_id).update(addr=addr_lit[0])

        return element_list


class EditElementForm(BaseForm):
    """ 修改元素信息 """
    id: int = Field(..., title="元素id")
    name: str = Field(..., title="元素名")
    by: str = Field(..., title="定位方式")
    element: str = Field(..., title="定位元素表达式")
    template_device: Optional[int] = Field(title="元素定位时参照的设备")
    desc: Optional[str] = Field(title="备注")
    wait_time_out: Optional[int] = Field(title="等待超时时间")

    async def validate_request(self, *args, **kwargs):
        element = await self.validate_data_is_exist("元素不存在", Element, id=self.id)

        # 校验元素名不重复
        await self.validate_data_is_not_repeat(
            f"当前页面下，名为【{self.name}】的元素已存在", Element, self.id, name=self.name, page_id=element.page_id)

        # 一个页面只能有一个url地址
        if self.by == "url":
            await self.validate_data_is_not_repeat(
                f"一个页面只能有一个地址", Element, self.id, page_id=element.page_id, by="url")

        return element


class ChangeElementByIdForm(BaseForm):
    """ 根据id更新元素 """
    id: int = Field(..., title="元素id")
    by: str = Field(..., title="定位方式")
    element: str = Field(..., title="定位元素表达式")

    async def validate_request(self, *args, **kwargs):
        return await self.validate_data_is_exist("元素不存在", Element, id=self.id)
