from typing import Optional, Union, List
from pydantic import Field

from ...baseForm import BaseForm, PaginationForm, ParamModel, HeaderModel, DataFormModel, ExtractModel, ValidateModel
from ..model_factory import ApiCase as Case, ApiStep as Step, ApiMsg as Api, ApiModule as Module, ApiProject as Project
from ...enums import ApiMethodEnum, ApiLevelEnum, DataStatusEnum, ApiBodyTypeEnum


class ApiListForm(PaginationForm):
    """ 查询接口信息 """
    module_id: int = Field(..., title="模块id")
    name: Optional[str] = Field(title="接口名")

    def get_query_filter(self, *args, **kwargs):
        """ 查询条件 """
        filter_dict = {"module_id": self.module_id}
        if self.name:
            filter_dict["name__icontains"] = self.name
        return filter_dict


class GetApiForm(BaseForm):
    """ 获取api信息 """
    id: int = Field(..., title="接口id")

    async def validate_api_is_exist(self):
        return await self.validate_data_is_exist("接口不存在", Api, id=self.id)

    async def validate_request(self, *args, **kwargs):
        return await self.validate_api_is_exist()


class DeleteApiForm(GetApiForm):
    """ 删除接口 """

    async def validate_request(self, *args, **kwargs):
        api = await self.validate_api_is_exist()
        # 校验接口是否被测试用例引用
        step = await Step.filter(api_id=self.id).first()
        if step:
            case = await Case.filter(id=step.case_id).first()
            raise ValueError(f"用例【{case.name}】已引用此接口，请先解除引用")
        return api


class AddApiForm(BaseForm):
    """ 添加接口信息的校验 """
    project_id: int = Field(..., title="服务id")
    module_id: int = Field(..., title="模块id")
    name: str = Field(..., title="接口名")
    desc: Optional[str] = Field(title="备注")
    up_func: Optional[list] = Field([], title="前置条件")
    down_func: Optional[list] = Field([], title="后置条件")
    method: ApiMethodEnum = Field(..., title="请求方法")
    addr: str = Field(..., title="接口地址")
    headers: List[HeaderModel] = Field(title="头部信息")
    params: List[ParamModel] = Field(title="url参数")
    body_type: ApiBodyTypeEnum = Field(..., title="请求体数据类型", description="json/form/text/urlencoded")
    data_form: List[DataFormModel] = Field(title="data-form参数")
    data_json: Union[list, dict] = Field(title="json参数")
    data_urlencoded: dict = Field(title="urlencoded参数")
    data_text: Optional[str] = Field(title="文本参数")
    extracts: List[ExtractModel] = Field(title="提取信息")
    validates: List[ValidateModel] = Field(title="断言信息")
    time_out: Optional[int] = Field(title="请求超时时间")

    async def validate_add_id_request(self, *args, **kwargs):
        await self.validate_data_is_exist("服务不存在", Project, id=self.project_id)
        await self.validate_data_is_exist("模块不存在", Module, id=self.module_id)

    async def validate_add_api_request(self, *args, **kwargs):
        # 校验数据结构
        self.validate_api_extracts([extract.dict() for extract in self.extracts])
        self.validate_base_validates([validate.dict() for validate in self.validates])
        self.validate_variable_format([data_form.dict() for data_form in self.data_form], msg_title='form-data')

    async def validate_request(self, *args, **kwargs):
        self.validate_is_true(self.addr, "接口地址必填")
        await self.validate_add_id_request()
        await self.validate_data_is_not_exist(
            f"当前模块下，名为【{self.name}】的接口已存在", Api, name=self.name, module_id=self.module_id)
        await self.validate_add_api_request()


class EditApiForm(GetApiForm, AddApiForm):
    """ 修改接口信息 """

    async def validate_request(self, *args, **kwargs):
        self.validate_is_true(self.addr, "接口地址必填")
        api = await self.validate_api_is_exist()
        await self.validate_add_id_request()
        await self.validate_data_is_not_repeat(
            f"当前模块下，名为【{self.name}】的接口已存在", Api, self.id, name=self.name, module_id=self.module_id)
        await self.validate_add_api_request()
        return api


class GetApiFromForm(BaseForm):
    """ 查询api归属 """
    id: Optional[int] = Field(title="接口id")
    addr: Optional[str] = Field(title="接口地址")

    async def validate_request(self, *args, **kwargs):
        self.validate_is_true("请传入接口地址或接口id", self.id or self.addr)

        if self.id:
            await self.validate_data_is_exist("接口不存在", Api, id=self.id)
            api_list = await Api.filter(id=self.id).all()
        else:
            api_list = await Api.filter(addr__icontains=self.addr).all()

        self.validate_is_true(api_list, "接口不存在")
        return api_list


class ChangeLevel(GetApiForm):
    level: str = Field(..., title="接口等级", description="P0、P1、P2")


class ChangeStatus(GetApiForm):
    status: DataStatusEnum = Field(..., title="接口状态", description="此接口状态，enable/disable")


class RunApiMsgForm(BaseForm):
    """ 运行接口 """
    project_id: int = Field(..., title="服务id")
    api_list: List[int] = Field(..., title="要运行的接口id")
    env_list: List[str] = Field(..., title="运行环境code")

    async def validate_request(self, *args, **kwargs):
        await self.validate_data_is_exist("服务不存在", Project, id=self.project_id)
        self.validate_is_true(self.api_list, "接口id必传")
        return await Api.filter(id__in=self.api_list).all()
