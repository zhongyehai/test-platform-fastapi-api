from app.baseModel import fields, BaseReport, BaseReportCase, BaseReportStep, pydantic_model_creator


class AppUiReport(BaseReport):
    class Meta:
        table = "app_ui_test_report"
        table_description = "APP测试报告表"


class AppUiReportCase(BaseReportCase):
    class Meta:
        table = "app_ui_test_report_case"
        table_description = "APP测试报告的用例数据表"


class AppUiReportStep(BaseReportStep):
    element_id = fields.IntField(description="步骤对应的元素id")

    class Meta:
        table = "app_ui_test_report_step"
        table_description = "APP测试报告的步骤数据表"


AppUiReportPydantic = pydantic_model_creator(AppUiReport, name="AppUiReport")
AppUiReportCasePydantic = pydantic_model_creator(AppUiReportCase, name="AppUiReportCase")
AppUiReportStepPydantic = pydantic_model_creator(AppUiReportStep, name="AppUiReportStep")
