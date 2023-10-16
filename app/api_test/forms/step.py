from typing import Optional, Union, List
from pydantic import Field

from ...baseForm import BaseForm, PaginationForm, ExtractModel, ValidateModel, HeaderModel, ParamModel, DataFormModel, \
    SkipIfModel
from ..model_factory import ApiStep as Step, ApiCase as Case, ApiMsg as Api
from ...enums import ApiBodyTypeEnum, DataStatusEnum


class GetStepListForm(PaginationForm):
    """ 根据用例id获取步骤列表 """
    case_id: int = Field(..., title="用例id")

    def get_query_filter(self, *args, **kwargs):
        """ 查询条件 """

        return {"case_id": self.case_id}


class GetStepForm(BaseForm):
    """ 根据步骤id获取步骤 """
    id: int = Field(..., title="步骤id")

    async def validate_step_is_exist(self):
        return await self.validate_data_is_exist("步骤不存在", Step, id=self.id)

    async def validate_request(self, *args, **kwargs):
        return await self.validate_step_is_exist()


class DeleteStepForm(BaseForm):
    """ 批量删除步骤 """
    id_list: list = Field(..., title="步骤id list")


class ChangeStepStatusForm(BaseForm):
    """ 批量修改步骤状态 """
    id_list: list = Field(..., title="步骤id list")
    status: DataStatusEnum = Field(..., title="步骤状态")


class CopyStepForm(GetStepForm):
    """ 复制步骤 """
    case_id: Optional[int] = Field(title="要复制到的用例id")


class AddStepForm(BaseForm):
    """ 添加步骤校验 """
    case_id: int = Field(..., title="步骤所属的用例id")
    quote_case: Optional[int] = Field(title="引用用例id（步骤为引用用例时必传）")
    name: str = Field(..., title="步骤名称")
    up_func: Optional[list] = Field(default=[], title="前置条件")
    down_func: Optional[list] = Field(default=[], title="后置条件")
    skip_if: List[SkipIfModel] = Field(..., title="跳过条件")
    run_times: int = Field(1, title="执行次数")
    extracts: List[ExtractModel] = Field(..., title="数据提取")
    skip_on_fail: int = Field(1, title="当用例有失败的步骤时，是否跳过此步骤")
    validates: List[ValidateModel] = Field(..., title="断言")
    data_driver: Union[list, dict] = Field([], title="数据驱动")

    api_id: Optional[int] = Field(title="步骤对应的接口id（步骤为接口时必传）")
    headers: List[HeaderModel] = Field(..., title="跳过条件")
    params: List[ParamModel] = Field(..., title="查询字符串参数")
    body_type: ApiBodyTypeEnum = Field(..., title="请求体数据类型", description="json/form/text/urlencoded")
    data_form: List[DataFormModel] = Field(..., title="form-data参数")
    data_json: Union[dict, list] = Field(..., title="json参数")
    data_urlencoded: dict = Field(..., title="urlencoded")
    data_text: Optional[str] = Field('', title="字符串参数")
    replace_host: int = Field(0, title="是否使用用例所在项目的域名")
    pop_header_filed: list = Field([], title="头部参数中去除指定字段")
    time_out: int = Field(60, title="请求超时时间")

    async def validate_add_step_request(self):
        if self.api_id:  # 引用用例没有接口id
            await self.validate_data_is_exist("接口数据不存在", Api, id=self.api_id)
        await self.validate_data_is_exist("用例不存在", Case, id=self.case_id)
        self.validate_is_true(f"不能自己引用自己", self.quote_case != self.case_id)

        if not self.quote_case:
            self.validate_api_extracts([extract.dict() for extract in self.extracts])
            self.validate_base_validates([validate.dict() for validate in self.validates])
            self.validate_variable_format([data_form.dict() for data_form in self.data_form], msg_title='form-data')

    async def validate_request(self, *args, **kwargs):
        await self.validate_add_step_request()


class EditStepForm(GetStepForm, AddStepForm):
    """ 修改步骤校验 """

    async def validate_request(self, *args, **kwargs):
        step = await self.validate_step_is_exist()
        await self.validate_add_step_request()
        return step
