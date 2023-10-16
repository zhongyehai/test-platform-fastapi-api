from app.baseModel import BaseCase, pydantic_model_creator


class AppUiCase(BaseCase):
    """ 用例表 """

    class Meta:
        table = "app_ui_test_case"
        table_description = "APP测试用例表"


AppUiCasePydantic = pydantic_model_creator(AppUiCase, name="AppUiCase")
