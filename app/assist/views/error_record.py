from typing import List
from fastapi import Request

from ..routers import assist_router
from ..model_factory import FuncErrorRecord, FuncErrorRecordPydantic
from ..forms.error_record import FindErrorForm


@assist_router.post("/errorRecord/list", response_model=List[FuncErrorRecordPydantic], summary="获取自定义函数错误列表")
async def get_error_record_list(form: FindErrorForm, request: Request):
    query_data = await form.make_pagination(FuncErrorRecord, user=request.state.user)
    return request.app.get_success(data=query_data)
