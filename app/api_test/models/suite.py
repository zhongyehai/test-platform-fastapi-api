# -*- coding: utf-8 -*-
from ...baseModel import BaseCaseSuite, fields, pydantic_model_creator


class ApiCaseSuite(BaseCaseSuite):
    """ 用例集表 """

    class Meta:
        table = "api_test_case_suite"
        table_description = "接口测试用例集表"


ApiCaseSuitePydantic = pydantic_model_creator(ApiCaseSuite, name="ApiCaseSuite")
