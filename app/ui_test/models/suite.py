from app.baseModel import BaseCaseSuite, pydantic_model_creator


class WebUiCaseSuite(BaseCaseSuite):
    """ 用例集表 """

    class Meta:
        table = "web_ui_test_case_suite"
        table_description = "web-ui测试用例集表"


WebUiCaseSuitePydantic = pydantic_model_creator(WebUiCaseSuite, name="WebUiCaseSuite")
