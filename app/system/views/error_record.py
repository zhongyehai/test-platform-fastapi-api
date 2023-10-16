from typing import List
from fastapi import Request

from ..routers import system_router
from ..forms.error_record import GetSystemErrorRecordList
from ..model_factory import SystemErrorRecord, SystemErrorRecordPydantic


@system_router.admin_post("/errorRecord/list", summary="获取系统报错记录的列表")
async def get_error_record_list(form: GetSystemErrorRecordList, request: Request):
    query_data = await form.make_pagination(SystemErrorRecord)
    return request.app.get_success(data=query_data)
