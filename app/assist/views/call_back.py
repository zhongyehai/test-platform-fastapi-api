from typing import List
from fastapi import Request

from ..routers import assist_router
from ..model_factory import CallBack, CallBackPydantic
from ..forms.call_back import FindCallBackForm


@assist_router.post("/callBack/list", response_model=List[CallBackPydantic], summary="获取回调列表")
async def call_back_list(form: FindCallBackForm, request: Request):
    query_data = await form.make_pagination(CallBack, user=request.state.user)
    return request.app.get_success(data=query_data)
