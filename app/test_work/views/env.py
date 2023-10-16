from typing import List
from fastapi import Request

from ..routers import test_work
from ..forms.env import GetEnvListForm, GetEnvForm, DeleteEnvForm, AddEnvForm, ChangeEnvForm
from ..model_factory import Env, EnvPydantic


@test_work.post("/env/list", response_model=List[EnvPydantic], summary="获取数据列表")
async def get_env_list(form: GetEnvListForm, request: Request):
    query_data = await form.make_pagination(Env, user=request.state.user)
    return request.app.get_success(data=query_data)


@test_work.login_post("/env/detail", summary="获取数据详情")
async def get_env_detail(form: GetEnvForm, request: Request):
    env = await form.validate_request(request)
    return request.app.get_success(data=env)


@test_work.login_post("/env", summary="新增数据")
async def add_env(form: AddEnvForm, request: Request):
    await form.validate_request(request)
    await Env.bulk_create([Env(create_user=request.user.id, **env.dict()) for env in form.data_list])
    return request.app.post_success()


@test_work.login_put("/env", summary="修改数据")
async def change_env(form: ChangeEnvForm, request: Request):
    env = await form.validate_request(request)
    await env.model_update(form.dict(), request.state.user)
    return request.app.put_success()


@test_work.login_delete("/env", summary="删除数据")
async def delete_env(form: DeleteEnvForm, request: Request):
    env = await form.validate_request(request)
    await env.model_delete()
    return request.app.delete_success()
