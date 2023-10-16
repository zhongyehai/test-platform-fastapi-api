from app.baseModel import BaseModule, fields, pydantic_model_creator


class AppUiModule(BaseModule):
    """ 模块表 """

    class Meta:
        table = "app_ui_test_module"
        table_description = "APP测试模块表"


AppUiModulePydantic = pydantic_model_creator(AppUiModule, name="AppUiModule")
