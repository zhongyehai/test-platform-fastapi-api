# -*- coding: utf-8 -*-
from ...baseModel import BaseTask, fields, pydantic_model_creator


class ApiTask(BaseTask):
    """ 定时任务表 """

    class Meta:
        table = "api_test_task"
        table_description = "接口测试任务表"


ApiTaskPydantic = pydantic_model_creator(ApiTask, name="ApiTask")
