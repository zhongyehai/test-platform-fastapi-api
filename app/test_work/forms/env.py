from typing import Optional, List
from pydantic import Field

from ...baseForm import BaseForm, PaginationForm
from ..model_factory import Env


class GetEnvListForm(PaginationForm):
    business: Optional[list] = Field(title="业务线")
    name: Optional[str] = Field(title="环境名")
    parent: Optional[str] = Field(title="当source_type为账号时，所属资源id")
    source_type: Optional[str] = Field(title="资源类型，账号:account、地址:addr")
    value: Optional[str] = Field(title="数据值")

    def get_query_filter(self, *args, **kwargs):
        """ 查询条件 """
        user, filter_dict = kwargs.get("user"), {}
        if self.name:
            filter_dict["name__icontains"] = self.name
        if self.value:
            filter_dict["value__icontains"] = self.value
        if self.source_type:
            filter_dict["source_type"] = self.source_type
        if self.source_type:
            filter_dict["source_type"] = self.source_type
        if self.parent:
            filter_dict["parent"] = self.parent
        else:
            filter_dict["business__in"] = self.business or user.business_list

        return filter_dict


class GetEnvForm(BaseForm):
    """ 数据详情 """
    id: int = Field(..., title="数据id")

    async def validate_env_is_exist(self):
        return await self.validate_data_is_exist("数据不存在", Env, id=self.id)

    async def validate_request(self, *args, **kwargs):
        return await self.validate_env_is_exist()


class DeleteEnvForm(GetEnvForm):
    """ 删除数据 """


class AddEnvDataForm(BaseForm):
    name: Optional[str] = Field(title="名字")
    value: Optional[str] = Field(title="值")
    password: Optional[str] = Field(title="密码")
    desc: Optional[str] = Field(title="值")


class AddEnvForm(BaseForm):
    """ 添加数据 """
    business: Optional[int] = Field(title="业务线")
    source_type: str = Field(..., title="资源类型")
    data_list: List[AddEnvDataForm] = Field(..., title="资源数据")
    parent: Optional[int] = Field(title="数据父级id")

    async def validate_request(self, *args, **kwargs):

        if self.source_type == "addr":  # 新增地址，则业务线必传
            self.validate_is_true('业务线必传', self.business)
        else:  # 新增账号，则父级id必传
            self.validate_is_true('父级资源必传', self.parent)

        for index, data in enumerate(self.data_list):
            if not data.name or not data.value:
                raise ValueError(f'第【{index + 1}】行，名字和值必填')


class ChangeEnvForm(GetEnvForm):
    """ 修改数据 """

    business: Optional[int] = Field(title="业务线")
    name: str = Field(..., title="资源名字")
    source_type: str = Field(..., title="资源类型")
    value: str = Field(..., title="资源对应的值")
    password: Optional[str] = Field(title="密码")
    parent: Optional[int] = Field(title="父级")
    desc: Optional[str] = Field(title="描述")
