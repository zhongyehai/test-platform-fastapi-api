from app.baseModel import BaseCaseSuite, pydantic_model_creator


class AppUiCaseSuite(BaseCaseSuite):
    """ 用例集表 """

    class Meta:
        table = "app_ui_test_case_suite"
        table_description = "APP测试用例集表"


AppUiCaseSuitePydantic = pydantic_model_creator(AppUiCaseSuite, name="AppUiCaseSuite")
