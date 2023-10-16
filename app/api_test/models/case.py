from ...baseModel import BaseCase, fields, pydantic_model_creator
from ..models.step import ApiStep as Step


class ApiCase(BaseCase):
    """ 用例表 """

    headers = fields.JSONField(default=[{"key": "", "value": "", "remark": ""}], description="用例的头部信息")

    class Meta:
        table = "api_test_case"
        table_description = "接口测试用例表"

    async def delete_current_and_step(self):
        step_list = await Step.filter(case_id=self.id).all()
        for step in step_list:
            await step.model_delete()
            await step.subtract_api_quote_count()
        await self.model_delete()


ApiCasePydantic = pydantic_model_creator(ApiCase, name="ApiCase")
