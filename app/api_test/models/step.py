# -*- coding: utf-8 -*-
from ..models.api import ApiMsg
from ...baseModel import BaseStep, fields, pydantic_model_creator
from ...enums import ApiBodyTypeEnum


class ApiStep(BaseStep):
    """ 测试步骤表 """

    time_out = fields.IntField(default=60, nullable=True, description="request超时时间，默认60秒")
    replace_host = fields.IntField(default=0,
                                   description="是否使用用例所在项目的域名，1使用用例所在服务的域名，0使用步骤对应接口所在服务的域名")
    headers = fields.JSONField(default=[{"key": None, "remark": None, "value": None}], description="头部信息")
    params = fields.JSONField(default=[{"key": None, "value": None}], description="url参数")
    data_form = fields.JSONField(
        default=[{"data_type": None, "key": None, "remark": None, "value": None}],
        description="form-data参数")
    data_urlencoded = fields.JSONField(default={}, description="form_urlencoded参数")
    data_json = fields.JSONField(default={}, description="json参数")
    data_text = fields.TextField(null=True, default="", description="文本参数")
    body_type = fields.CharEnumField(ApiBodyTypeEnum, default=ApiBodyTypeEnum.JSON, description="请求体数据类型，json/form/text/urlencoded")
    extracts = fields.JSONField(
        default=[
            {"status": 1, "key": None, "data_source": None, "value": None, "remark": None, "update_to_header": None}],
        description="提取信息"
    )
    validates = fields.JSONField(
        default=[{"status": 1, "key": None, "value": None, "remark": None, "data_type": None, "data_source": None,
                  "validate_type": "data", "validate_method": None}],
        description="断言信息")

    pop_header_filed = fields.JSONField(default=[], description="头部参数中去除指定字段")

    api_id = fields.IntField(null=True, default=None, description="步骤所引用的接口的id")

    class Meta:
        table = "api_test_step"
        table_description = "接口测试用例步骤表"

    async def add_quote_count(self, api=None):
        """ 步骤对应的接口被引用次数+1 """
        if not self.quote_case:
            if not api:
                api = await ApiMsg.filter(id=self.api_id).first()
            await api.add_quote_count()

    async def subtract_api_quote_count(self, api=None):
        """ 步骤对应的被引用次数-1 """
        if not self.quote_case:
            if not api:
                api = await ApiMsg.filter(id=self.api_id).first()
            await api.subtract_quote_count()


ApiStepPydantic = pydantic_model_creator(ApiStep, name="ApiStep")
