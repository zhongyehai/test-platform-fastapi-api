from fastapi import Request, Depends

from ...schemas.autotest import project as schema
from ...models.assist.model_factory import Script
from ...models.autotest.model_factory import ModelSelector
from ...models.system.user import User
from ...models.config.model_factory import RunEnv


async def get_project_list(request: Request, form: schema.FindProjectListForm = Depends()):
    models = ModelSelector(request.app.test_type)
    get_filed = ["id", "name", "business_id"]
    if form.detail:
        get_filed.extend(["manager", "update_user"])
        if request.app.test_type == "api":
            get_filed.extend(["source_type", "source_addr", "last_pull_status"])
        elif request.app.test_type == "app":
            get_filed.extend(["app_package", "template_device"])

    query_data = await form.make_pagination(models.project, user=request.state.user, get_filed=get_filed)
    return request.app.get_success(data=query_data)


async def project_sort(request: Request, form: schema.ChangeSortForm):
    models = ModelSelector(request.app.test_type)
    await models.project.change_sort(**form.dict(exclude_unset=True))
    return request.app.put_success()


async def get_project_detail(request: Request, form: schema.GetProjectForm = Depends()):
    models = ModelSelector(request.app.test_type)
    project = await models.project.filter(id=form.id).first()
    return request.app.get_success(project)


async def add_project(request: Request, form: schema.AddProjectForm):
    await form.validate_request()
    models = ModelSelector(request.app.test_type)

    project = await models.project.model_create(form.dict(), request.state.user)
    # 新增服务的时候，一并把运行环境、用例集设置齐全
    await models.env.create_env(RunEnv, models.project, project.id)
    await models.suite.create_suite_by_project(project.id)

    return request.app.post_success(data=project)


async def change_project(request: Request, form: schema.EditProjectForm):
    await form.validate_request()
    models = ModelSelector(request.app.test_type)
    data = form.get_update_data(request.state.user.id)
    if request.app.test_type != "app":
        data.pop("app_package")
        data.pop("app_activity")
        data.pop("template_device")
    if request.app.test_type != "api":
            data.pop("source_type")
            data.pop("source_addr")
            data.pop("source_name")
            data.pop("source_id")

    await models.project.filter(id=form.id).update(**data)
    return request.app.put_success()


async def delete_project(request: Request, form: schema.GetProjectForm):
    """ 删除服务 / app / 项目 """
    models = ModelSelector(request.app.test_type)
    project = await models.project.filter(id=form.id).first()

    # 删除权限判断，管理员、数据创建者、服务负责人
    if User.is_not_admin(request.state.user.api_permissions):
        if request.state.user.id not in [project.create_user, project.manager]:
            raise ValueError("当前用户无权限删除此服务")

    await models.task.filter(project_id=project.id).delete()  # 删除任务
    await models.suite.filter(project_id=project.id).delete()  # 删除用例集
    await models.module.filter(project_id=project.id).delete()  # 删除模块
    await project.model_delete()  # 删除服务
    return request.app.delete_success()


async def synchronization_project_env(request: Request, form: schema.SynchronizationEnvForm):
    models = ModelSelector(request.app.test_type)
    from_env = await models.env.validate_is_exist("环境不存在", project_id=form.project_id, env_id=form.env_from)
    filed_list = ["variables", "headers"] if request.app.test_type == "api" else ["variables"]
    await models.env.synchronization(dict(from_env), form.env_to, filed_list)
    return request.app.success("同步完成")


async def get_project_env(request: Request, form: schema.GetEnvForm = Depends()):
    models = ModelSelector(request.app.test_type)
    env_data = await models.env.filter(env_id=form.env_id, project_id=form.project_id).first()
    if not env_data:  # 如果没有就插入一条记录， 并且自动同步当前服务已有的环境数据
        env_data = await models.env.insert_env(form.project_id, form.env_id, request.state.user.id)
    return request.app.get_success(env_data)


async def change_project_env(request: Request, form: schema.EditEnvForm):
    models = ModelSelector(request.app.test_type)
    project_env = await models.env.validate_is_exist("环境不存在", id=form.id)
    project = await models.project.filter(id=project_env.project_id).first().values("script_list")
    all_func_name = await Script.get_func_by_script_id(project["script_list"])
    await form.validate_request(all_func_name=all_func_name)

    update_data = form.dict()
    if request.app.test_type != "api":
        update_data.pop("headers")
    await project_env.model_update(update_data,  request.state.user)

    # 把环境的头部信息、变量的key一并同步到其他环境
    project_env_list = await models.env.filter(
        project_id=project_env.project_id, id__not=project_env.env_id).values("env_id")
    await models.env.synchronization(
        form.dict(),
        [env["env_id"] for env in project_env_list],
        ["variables", "headers"] if request.app.test_type == "api" else ["variables"])

    return request.app.put_success()
