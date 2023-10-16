from typing import List
from fastapi import Request

from ..routers import api_test
from ...baseForm import ChangeSortForm
from ...busines import ProjectBusiness
from ..model_factory import ApiProject as Project, ApiProjectEnv as ProjectEnv, ApiProjectPydantic as ProjectPydantic, \
    ApiModule as Module, ApiCaseSuite as CaseSuite, ApiTask as Task
from ..forms.project import GetProjectForm, FindProjectListForm, AddProjectForm, DeleteProjectForm, EditProjectForm, \
    GetEnvForm, EditEnvForm, SynchronizationEnvForm


@api_test.login_post("/project/list", response_model=List[ProjectPydantic], summary="获取服务列表")
async def api_get_project_list(form: FindProjectListForm, request: Request):
    query_data = await form.make_pagination(Project, user=request.state.user)
    return request.app.get_success(data=query_data)


@api_test.login_post("/project/sort", summary="服务列表排序")
async def api_project_sort(form: ChangeSortForm, request: Request):
    await Project.change_sort(**form.dict(exclude_unset=True))
    return request.app.put_success()


@api_test.login_post("/project/detail", summary="获取服务详情")
async def api_get_project_detail(form: GetProjectForm, request: Request):
    project = await form.validate_request()
    return request.app.get_success(project)


@api_test.login_post("/project", summary="新增服务")
async def api_add_project(form: AddProjectForm, request: Request):
    await form.validate_request()
    project = await ProjectBusiness.add_project(form.dict(), request, Project, ProjectEnv, CaseSuite)
    return request.app.post_success(data=project)


@api_test.login_put("/project", summary="修改服务")
async def api_change_project(form: EditProjectForm, request: Request):
    project = await form.validate_request()
    await project.model_update(form.dict(), request.state.user)
    return request.app.put_success()


@api_test.login_delete("/project", summary="删除服务")
async def api_delete_project(form: DeleteProjectForm, request: Request):
    project = await form.validate_request(request.state.user)
    await ProjectBusiness.delete_project(project, Module, CaseSuite, Task)
    return request.app.delete_success()


@api_test.login_put("/project/env/synchronization", summary="同步环境数据")
async def api_synchronization_project_env(form: SynchronizationEnvForm, request: Request):
    from_env = await form.validate_request()
    await ProjectEnv.synchronization(dict(from_env), form.env_to, ["variables", "headers"])
    return request.app.success("同步完成")


@api_test.login_post("/project/env", summary="获取服务环境")
async def api_get_project_env(form: GetEnvForm, request: Request):
    env_data = await form.validate_request(request.state.user)
    return request.app.get_success(env_data)


@api_test.login_put("/project/env", summary="修改服务环境")
async def api_change_project_env(form: EditEnvForm, request: Request):
    project_env = await form.validate_request()
    await ProjectBusiness.chang_env(project_env, form.dict(), request.state.user, ["variables", "headers"])
    return request.app.put_success()
