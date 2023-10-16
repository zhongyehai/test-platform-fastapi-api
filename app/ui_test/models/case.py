from app.baseModel import BaseCase, pydantic_model_creator


class WebUiCase(BaseCase):
    """ 用例表 """

    class Meta:
        table = "web_ui_test_case"
        table_description = "web-ui测试用例表"


WebUiCasePydantic = pydantic_model_creator(WebUiCase, name="WebUiCase")
