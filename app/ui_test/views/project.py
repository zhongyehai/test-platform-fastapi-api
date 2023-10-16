from typing import List
from fastapi import Request

from ..routers import ui_test
from ..model_factory import WebUiProject as Project, WebUiProjectEnv as ProjectEnv, \
    WebUiProjectPydantic as ProjectPydantic, WebUiProjectEnvPydantic as ProjectEnvPydantic, WebUiModule as Module, \
    WebUiCaseSuite as CaseSuite, WebUiTask as Task
from ..forms.project import GetProjectForm, FindProjectListForm, AddProjectForm, DeleteProjectForm, EditProjectForm, \
    GetEnvForm, EditEnvForm, SynchronizationEnvForm
from ...baseForm import ChangeSortForm
from ...busines import ProjectBusiness


@ui_test.login_post("/project/list", response_model=List[ProjectPydantic], summary="获取项目列表")
async def ui_get_project_list(form: FindProjectListForm, request: Request):
    query_data = await form.make_pagination(Project, user=request.state.user)
    return request.app.get_success(data=query_data)


@ui_test.login_post("/project/sort", summary="项目列表排序")
async def ui_change_project_sort(form: ChangeSortForm, request: Request):
    await Project.change_sort(**form.dict(exclude_unset=True))
    return request.app.put_success()


@ui_test.login_post("/project/detail", summary="获取项目详情")
async def ui_get_project_detail(form: GetProjectForm, request: Request):
    project = await form.validate_request(request)
    return request.app.get_success(project)


@ui_test.login_post("/project", summary="新增项目")
async def ui_add_project(form: AddProjectForm, request: Request):
    await form.validate_request(request)
    project = await ProjectBusiness.add_project(form.dict(), request, Project, ProjectEnv, CaseSuite)
    return request.app.post_success(data=project)


@ui_test.login_put("/project", summary="修改项目")
async def ui_change_project(form: EditProjectForm, request: Request):
    project = await form.validate_request(request)
    await project.model_update(form.dict(), request.state.user)
    return request.app.put_success()


@ui_test.login_delete("/project", summary="删除项目")
async def ui_delete_project(form: DeleteProjectForm, request: Request):
    project = await form.validate_request(request)
    await ProjectBusiness.delete_project(project, Module, CaseSuite, Task)
    return request.app.delete_success()


@ui_test.login_put("/project/env/synchronization", summary="同步环境数据")
async def ui_synchronization_project_env(form: SynchronizationEnvForm, request: Request):
    from_env = await form.validate_request(request)
    await ProjectEnv.synchronization(dict(from_env), form.env_to, ["variables"])
    return request.app.success("同步完成")


@ui_test.login_post("/project/env", summary="获取项目环境")
async def ui_get_project_env(form: GetEnvForm, request: Request):
    env_data = await form.validate_request(request)
    return request.app.get_success(env_data)


@ui_test.login_put("/project/env", summary="修改项目环境")
async def ui_get_project_env(form: EditEnvForm, request: Request):
    project_env = await form.validate_request()
    await ProjectBusiness.chang_env(project_env, form.dict(), request.state.user, ["variables"])
    return request.app.put_success()
