from typing import List
from fastapi import Request

from ..routers import assist_router
from ..forms.hits import GetHitListForm, GetHitForm, CreatHitForm, EditHitForm
from ..model_factory import Hits, HitsPydantic


@assist_router.login_post("/hit/type/list", summary="自动化测试命中问题类型列表")
async def get_hit_type_list(request: Request):
    hit_type_list = await Hits.all().distinct().values("hit_type")
    return request.app.get_success(
        data=[{"key": hit_type[0], "value": hit_type[0]} for hit_type in hit_type_list])


@assist_router.login_post("/hit/list", response_model=List[HitsPydantic], summary="自动化测试命中问题列表")
async def get_hit_list(form: GetHitListForm, request: Request):
    query_data = await form.make_pagination(Hits, user=request.state.user)
    return request.app.get_success(data=query_data)


@assist_router.login_post("/hit/detail", summary="获取自动化测试命中问题")
async def get_hit_detail(form: GetHitForm, request: Request):
    data = await form.validate_request()
    return request.app.get_success(data)


@assist_router.login_post("/hit", summary="新增自动化测试命中问题")
async def add_hit(form: CreatHitForm, request: Request):
    await form.validate_request()
    hit = await Hits.model_create(form.dict(), request.state.user)
    return request.app.post_success(data=hit)


@assist_router.login_put("/hit", summary="修改自动化测试命中问题")
async def change_hit(form: EditHitForm, request: Request):
    hit = await form.validate_request()
    await hit.model_update(form.dict(), request.state.user)
    return request.app.put_success()


@assist_router.login_delete("/hit", summary="删除自动化测试命中问题")
async def delete_hit(form: GetHitForm, request: Request):
    hit = await form.validate_request(request.state.user)
    await hit.model_delete()
    return request.app.delete_success()
