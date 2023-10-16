from app.baseModel import BaseModel, fields, pydantic_model_creator, SaveRequestLog


class SystemErrorRecord(SaveRequestLog):
    detail = fields.TextField(null=True, description="错误详情")

    class Meta:
        table = "system_error_record"
        table_description = "系统错误记录表"


SystemErrorRecordPydantic = pydantic_model_creator(SystemErrorRecord, name="SystemErrorRecord")
