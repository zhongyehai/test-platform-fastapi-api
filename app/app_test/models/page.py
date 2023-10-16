from app.baseModel import BaseApi, fields, pydantic_model_creator


class AppUiPage(BaseApi):
    """ 页面表 """

    class Meta:
        table = "app_ui_test_page"
        table_description = "APP测试页面表"


AppUiPagePydantic = pydantic_model_creator(AppUiPage, name="AppUiPage")
