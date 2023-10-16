from ...baseModel import fields, BaseReport, BaseReportCase, BaseReportStep, pydantic_model_creator


class ApiReport(BaseReport):
    class Meta:
        table = "api_test_report"
        table_description = "接口测试报告表"


class ApiReportCase(BaseReportCase):
    class Meta:
        table = "api_test_report_case"
        table_description = "测试报告用例表"


class ApiReportStep(BaseReportStep):
    api_id = fields.IntField(description="步骤对应的接口id")

    class Meta:
        table = "api_test_report_step"
        table_description = "接口测试报告的步骤数据表"


ApiReportPydantic = pydantic_model_creator(ApiReport, name="ApiReport")
ApiReportCasePydantic = pydantic_model_creator(ApiReportCase, name="ApiReportCase")
ApiReportStepPydantic = pydantic_model_creator(ApiReportStep, name="ApiReportStep")
