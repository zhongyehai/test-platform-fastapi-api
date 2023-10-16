import json
from typing import Optional, Union
from pydantic import Field

from ...baseForm import BaseForm, PaginationForm
from ..model_factory import WebUiElement as Element, WebUiCase as Case, WebUiStep as Step
from ...enums import DataStatusEnum


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
    skip_if: list = Field(..., title="跳过条件")
    run_times: int = Field(1, title="执行次数")
    extracts: list = Field(..., title="数据提取")
    skip_on_fail: int = Field(1, title="当用例有失败的步骤时，是否跳过此步骤")
    validates: list = Field(..., title="断言")
    data_driver: Union[list, dict] = Field([], title="数据驱动")

    element_id: Optional[int] = Field(title="步骤对应的元素id（步骤为元素时必传）")
    execute_type: Optional[str] = Field(title="执行动作")
    send_keys: Optional[str] = Field(title="输入文本内容")
    wait_time_out: int = Field(5, title="等待元素超时时间")

    async def validate_add_step_request(self):
        if self.element_id:  # 引用用例没有元素id
            await self.validate_data_is_exist("元素数据不存在", Element, id=self.element_id)
        await self.validate_data_is_exist("用例不存在", Case, id=self.case_id)
        self.validate_is_true("不能自己引用自己", self.quote_case != self.case_id)

        if not self.quote_case:
            if not self.execute_type:
                raise ValueError("执行方式不能为空")
            if "dict" in self.execute_type:  # 校验输入字典的项能不能序列化和反序列化
                if self.send_keys.startswith("$") is False:
                    try:
                        self.loads(self.send_keys)
                    except Exception as error:
                        raise ValueError(f"【{self.send_keys}】不能转为json，请确认")

            self.validate_ui_extracts(self.extracts)  # 校验数据提取信息
            self.validate_base_validates(self.validates)  # 校验断言信息

    async def validate_request(self, *args, **kwargs):
        await self.validate_add_step_request()


class EditStepForm(GetStepForm, AddStepForm):
    """ 修改步骤校验 """

    async def validate_request(self, *args, **kwargs):
        step = await self.validate_step_is_exist()
        await self.validate_add_step_request()
        return step
