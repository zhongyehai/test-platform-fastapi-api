from app.baseModel import fields, BaseReport, BaseReportCase, BaseReportStep, pydantic_model_creator


class WebUiReport(BaseReport):
    class Meta:
        table = "web_ui_test_report"
        table_description = "web-ui测试报告表"


class WebUiReportCase(BaseReportCase):
    class Meta:
        table = "web_ui_test_report_case"
        table_description = "web-ui测试报告的用例数据表"


class WebUiReportStep(BaseReportStep):
    element_id = fields.IntField(description="步骤对应的元素id")

    class Meta:
        table = "web_ui_test_report_step"
        table_description = "web-ui测试报告的步骤数据表"


WebUiReportPydantic = pydantic_model_creator(WebUiReport, name="WebUiReport")
WebUiReportCasePydantic = pydantic_model_creator(WebUiReportCase, name="WebUiReportCase")
WebUiReportStepPydantic = pydantic_model_creator(WebUiReportStep, name="WebUiReportStep")
