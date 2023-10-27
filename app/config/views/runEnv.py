from typing import List
from fastapi import Request

from ..routers import config_router
from app.config.model_factory import RunEnv, RunEnvPydantic, BusinessLine
from ..forms.runEnv import GetRunEnvForm, PostRunEnvForm, PutRunEnvForm, DeleteRunEnvForm, \
    GetRunEnvListForm, EnvToBusinessForm, ChangeEnvSortForm
from ...busines import ProjectEnvBusiness


@config_router.post("/env/list", response_model=List[RunEnvPydantic], summary="获取运行环境列表")
async def get_run_env_list(form: GetRunEnvListForm, request: Request):
    validate_filter = await form.validate_request()
    query_data = await form.make_pagination(RunEnv, validate_filter=validate_filter)
    return request.app.get_success(data=query_data)


@config_router.login_put("/env/business", summary="批量绑定/解除绑定环境与业务线的关系")
async def batch_to_business(form: EnvToBusinessForm, request: Request):
    await RunEnv.env_to_business(form.env_list, form.business_list, form.command)
    return request.app.put_success()


@config_router.login_post("/env/group", response_model=RunEnvPydantic, summary="环境分组列表")
async def get_run_env_group(request: Request):
    group_list = await RunEnv.all().distinct().values("group")
    return request.app.get_success(data=[group["group"] for group in group_list])


@config_router.login_put("/env/sort", summary="修改环境排序")
async def change_run_env_sort(form: ChangeEnvSortForm, request: Request):
    await RunEnv.change_sort(**form.dict(exclude_unset=True))
    return request.app.put_success()


@config_router.login_post("/env/detail", summary="获取环境详情")
async def get_run_env_detail(form: GetRunEnvForm, request: Request):
    env = await form.validate_request(request)
    return request.app.get_success(env)


@config_router.admin_post("/env", summary="新增环境")
async def add_run_env(form: PostRunEnvForm, request: Request):
    await form.validate_request(request)
    run_env = await RunEnv.model_create(form.dict(), request.state.user)

    # 给所有的服务/项目/app创建此运行环境的数据
    await ProjectEnvBusiness.add_env(run_env.id)

    # 把环境分配给设置了自动绑定的业务线
    business_list = await BusinessLine.get_auto_bind_env_id_list()
    await RunEnv.env_to_business([run_env.id], business_list, "add")

    return request.app.post_success()


@config_router.login_put("/env", summary="修改环境")
async def change_run_env(form: PutRunEnvForm, request: Request):
    env = await form.validate_request(request)
    await env.model_update(form.dict(), request.state.user)
    return request.app.put_success()


@config_router.login_delete("/env", summary="删除环境")
async def delete_run_env(form: DeleteRunEnvForm, request: Request):
    env = await form.validate_request(request)
    await env.model_delete()
    return request.app.delete_success()
