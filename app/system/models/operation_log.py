# -*- coding: utf-8 -*-
from app.baseModel import SaveRequestLog, pydantic_model_creator


class OperationLog(SaveRequestLog):
    """ 用户操作记录表 """

    class Meta:
        table = "system_user_operation_log"
        table_description = "用户操作记录表"


OperationLogRecordPydantic = pydantic_model_creator(OperationLog, name="OperationLog")
