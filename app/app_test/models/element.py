from app.baseModel import BaseElement, fields, pydantic_model_creator


class AppUiElement(BaseElement):
    """ 页面元素表 """

    template_device = fields.IntField(null=True, description="元素定位时参照的设备，定位方式为bounds时根据此设备参照分辨率")

    class Meta:
        table = "app_ui_test_element"
        table_description = "APP测试元素表"


AppUiElementPydantic = pydantic_model_creator(AppUiElement, name="AppUiElement")
