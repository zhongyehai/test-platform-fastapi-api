from app.baseModel import BaseApi, fields, pydantic_model_creator


class WebUiPage(BaseApi):
    """ 页面表 """

    addr = fields.CharField(255, null=True, default='', description="地址")

    class Meta:
        table = "web_ui_test_page"
        table_description = "web-ui测试页面表"


WebUiPagePydantic = pydantic_model_creator(WebUiPage, name="WebUiPage")
