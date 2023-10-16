from app.baseModel import BaseModule, fields, pydantic_model_creator


class WebUiModule(BaseModule):
    """ 模块表 """

    class Meta:
        table = "web_ui_test_module"
        table_description = "web-ui测试模块表"


WebUiModulePydantic = pydantic_model_creator(WebUiModule, name="WebUiModule")
