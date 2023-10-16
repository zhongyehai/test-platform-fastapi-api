from typing import Optional
from pydantic import Field

from ...baseForm import BaseForm, PaginationForm
from ..model_factory import DataPool


class GetDataPoolListForm(PaginationForm):
    """ 获取数据池列表/新增数据池数据 """
    env: Optional[str] = Field(title="环境")
    mobile: Optional[str] = Field(title="手机号")
    business_order_no: Optional[str] = Field(title="订单号")
    business_status: Optional[str] = Field(title="业务状态")
    use_status: Optional[str] = Field(title="使用状态")

    def get_query_filter(self, *args, **kwargs):
        """ 查询条件 """
        filter_dict = {}
        if self.env:
            filter_dict["env__icontains"] = self.env
        if self.mobile:
            filter_dict["mobile__icontains"] = self.mobile
        if self.business_order_no:
            filter_dict["business_order_no__icontains"] = self.business_order_no
        if self.business_status:
            filter_dict["business_status__icontains"] = self.business_status
        if self.use_status:
            filter_dict["use_status__icontains"] = self.use_status
        return filter_dict


class GetDataPoolForm(BaseForm):
    """ 校验数据池数据存在 """
    id: int = Field(..., title="数据id")

    async def get_data_pool_form(self):
        return await self.validate_data_is_exist('数据不存在', DataPool, id=self.id)

    async def validate_request(self, *args, **kwargs):
        return await self.get_data_pool_form()


class DeleteDataPoolForm(GetDataPoolForm):
    """ 删除数据池数据 """

    async def validate_request(self, *args, **kwargs):
        return await self.get_data_pool_form()


class PostDataPoolForm(BaseForm):
    """ 新增数据池数据 """
    env: str = Field(..., title="环境")
    desc: str = Field(title="描述文字")
    mobile: str = Field(title="手机号")
    password: str = Field(title="密码")
    business_order_no: str = Field(title="流水号")


class PutDataPoolForm(GetDataPoolForm, PostDataPoolForm):
    """ 修改数据池数据 """

    async def validate_request(self, *args, **kwargs):
        return await self.get_data_pool_form()


class GetAutoTestUserDataListForm(PaginationForm):
    """ 获取自动化用户数据 """
    env: Optional[str] = Field(title="环境")

    def get_query_filter(self, *args, **kwargs):
        """ 查询条件 """
        filter_dict = {}
        if self.env:
            filter_dict["env"] = self.env
        return filter_dict
