from typing import List
from fastapi import Request

from ..routers import assist_router
from ..forms.data_pool import GetDataPoolListForm, GetDataPoolForm, PutDataPoolForm, DeleteDataPoolForm, \
    PostDataPoolForm, GetAutoTestUserDataListForm
from ..model_factory import AutoTestUser, DataPool, AutoTestUserPydantic, DataPoolPydantic


@assist_router.login_post("/autoTestUser", summary="获取自动化测试用户数据列表")
async def get_auto_test_user_list(form: GetAutoTestUserDataListForm, request: Request):
    query_data = await form.make_pagination(AutoTestUser, user=request.state.user)
    return request.app.get_success(data=query_data)


@assist_router.login_post("/dataPool/list", response_model=List[DataPoolPydantic], summary="获取数据池列表")
async def get_data_pool_list(form: GetDataPoolListForm, request: Request):
    query_data = await form.make_pagination(DataPool, user=request.state.user)
    return request.app.get_success(data=query_data)


@assist_router.login_post("/dataPool/businessStatus", summary="获取数据池业务状态")
async def get_data_pool_business_status(request: Request):
    business_status = await DataPool.all().distinct().values("business_status")
    return request.app.get_success(data=business_status)


@assist_router.login_post("/dataPool/useStatus", summary="获取数据池使用状态")
async def get_data_pool_use_status(request: Request):
    return request.app.get_success(data={"not_used": "未使用", "in_use": "使用中", "used": "已使用"})


@assist_router.login_post("/dataPool/detail", summary="获取数据详情")
async def get_data_pool_detail(form: GetDataPoolForm, request: Request):
    data = await form.validate_request()
    return request.app.get_success(data)


@assist_router.login_post("/dataPool", summary="新增数据")
async def add_data_pool(form: PostDataPoolForm, request: Request):
    data_pool = await DataPool.model_create(form.dict(), request.state.user)
    return request.app.post_success(data=data_pool)


@assist_router.login_put("/dataPool", summary="修改数据")
async def change_data_pool(form: PutDataPoolForm, request: Request):
    data_pool = await form.validate_request()
    await data_pool.model_update(form.dict(), request.state.user)
    return request.app.put_success()


@assist_router.login_delete("/dataPool", summary="删除数据")
async def delete_data_pool(form: DeleteDataPoolForm, request: Request):
    data_pool = await form.validate_request(request.state.user)
    await data_pool.model_delete()
    return request.app.delete_success()
