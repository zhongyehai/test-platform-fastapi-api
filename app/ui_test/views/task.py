from typing import List
from fastapi import Request, BackgroundTasks

from ..routers import ui_test
from ...baseForm import ChangeSortForm
from ...busines import TaskBusiness, RunCaseBusiness
from ..model_factory import WebUiReport as Report, WebUiCase as Case, WebUiCaseSuite as CaseSuite, WebUiTask as Task, \
    WebUiTaskPydantic as TaskPydantic
from ..forms.task import RunTaskForm, AddTaskForm, EditTaskForm, GetTaskForm, DeleteTaskForm, \
    GetTaskListForm
from utils.client.run_ui_test import RunCase


@ui_test.login_post("/task/list", response_model=List[TaskPydantic], summary="获取任务列表")
async def ui_get_task_list(form: GetTaskListForm, request: Request):
    query_data = await form.make_pagination(Task, user=request.state.user)
    return request.app.get_success(data=query_data)


@ui_test.login_put("/task/sort", summary="任务列表排序")
async def ui_change_task_sort(form: ChangeSortForm, request: Request):
    await Task.change_sort(**form.dict(exclude_unset=True))
    return request.app.put_success()


@ui_test.login_post("/task/copy", summary="复制定时任务")
async def ui_copy_task(form: GetTaskForm, request: Request):
    task = await form.validate_request()
    new_task = await TaskBusiness.copy(task, Task, request.state.user)
    return request.app.success("复制成功", data=new_task)


@ui_test.login_post("/task/detail", summary="获取任务详情")
async def ui_get_task_detail(form: GetTaskForm, request: Request):
    suite = await form.validate_request(request)
    return request.app.get_success(data=suite)


@ui_test.login_post("/task", summary="新增任务")
async def ui_add_task(form: AddTaskForm, request: Request):
    await form.validate_request(request)
    await Task.model_create(form.dict(), request.state.user)
    return request.app.post_success()


@ui_test.login_put("/task", summary="修改任务")
async def ui_change_task(form: EditTaskForm, request: Request):
    task = await form.validate_request(request)
    await task.model_update(form.dict(), request.state.user)
    return request.app.put_success()


@ui_test.login_delete("/task", summary="删除任务")
async def ui_delete_task(form: DeleteTaskForm, request: Request):
    task = await form.validate_request(request)
    await task.model_delete()
    return request.app.delete_success()


@ui_test.login_put("/task/enable", summary="启用定时任务")
async def ui_enable_task(form: GetTaskForm, request: Request):
    task = await form.validate_request(request)
    res = await TaskBusiness.enable(task, "webUi", request.state.user, request.headers.get("X-Token"))
    if res["status"] == 1:
        return request.app.success("任务启用成功", data=res["data"])
    else:
        return request.app.fail("任务启用失败", data=res["data"])


@ui_test.login_put("/task/disable", summary="关闭定时任务")
async def ui_disable_task(form: GetTaskForm, request: Request):
    task = await form.validate_request(request)
    res = await TaskBusiness.disable(task, "webUi", request.headers.get("X-Token"))
    if res['status'] == 1:
        return request.app.success("任务禁用成功", data=res["data"])
    else:
        return request.app.fail("任务禁用失败", data=res["data"])


@ui_test.login_post("/task/run", summary="运行任务")
async def ui_run_task(form: RunTaskForm, request: Request, background_tasks: BackgroundTasks):
    task = await form.validate_request(request)
    case_id_list = await CaseSuite.get_case_id(Case, task.project_id, task.suite_ids, task.case_ids)
    batch_id = Report.get_batch_id(request.state.user.id)
    env_list = form.env_list or task.env_list
    for env_code in env_list:
        report_id = await RunCaseBusiness.run(
            batch_id=batch_id,
            env_code=env_code,
            browser=form.browser or task.browser,
            trigger_type=form.trigger_type,
            is_async=form.is_async,
            project_id=task.project_id,
            report_name=task.name,
            task_type="task",
            report_model=Report,
            trigger_id=form.id,
            case_id_list=case_id_list,
            run_type="webUi",
            runner=RunCase,
            extend_data=form.extend,
            task_dict=dict(task),
            create_user=request.state.user.id
        )

    return request.app.trigger_success(
        data={
            "batch_id": batch_id,
            "report_id": report_id if len(env_list) == 1 else None
        })
