# -*- coding: utf-8 -*-
from ...baseModel import BaseModule, fields, pydantic_model_creator


class ApiModule(BaseModule):
    """ 模块表 """

    controller = fields.CharField(255, null=True, default=None, description="当前模块在swagger上的controller名字")

    class Meta:
        table = "api_test_module"
        table_description = "接口测试模块表"


ApiModulePydantic = pydantic_model_creator(ApiModule, name="ApiModule")
