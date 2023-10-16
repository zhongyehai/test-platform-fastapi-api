from app.baseModel import BaseElement, fields, pydantic_model_creator


class WebUiElement(BaseElement):
    """ 页面元素表 """

    class Meta:
        table = "web_ui_test_element"
        table_description = "web-ui测试元素表"


WebUiElementPydantic = pydantic_model_creator(WebUiElement, name="WebUiElement")
