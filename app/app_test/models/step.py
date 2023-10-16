# -*- coding: utf-8 -*-
from app.baseModel import BaseStep, fields, pydantic_model_creator


class AppUiStep(BaseStep):
    """ 测试步骤表 """

    wait_time_out = fields.IntField(default=10, null=True, description="等待元素出现的时间，默认10秒")
    execute_type = fields.CharField(255, description="执行方式")
    send_keys = fields.CharField(255, description="要输入的文本内容")
    extracts = fields.JSONField(
        default=[{"key": None, "extract_type": None, "value": None, "remark": None}],
        description="提取信息"
    )
    validates = fields.JSONField(
        default=[{"data_source": None, "key": None, "validate_type": "page", "validate_method": None, "data_type": None,
                  "value": None, "remark": None}],
        description="断言信息")
    element_id = fields.IntField(null=True, description="步骤所引用的元素的id")

    class Meta:
        table = "app_ui_test_step"
        table_description = "APP测试步骤表"

    def add_quote_count(self):
        pass


AppUiStepPydantic = pydantic_model_creator(AppUiStep, name="AppUiStep")
