from fastapi import Request, Body

from app.hooks.error_hook import register_exception_handler
from app.hooks.request_hook import register_request_hook
from app.hooks.app_hook import register_app_hook
from app.system.forms.job import GetJobForm
from app.baseView import FastAPI
from config import job_server_port
from utils.util.request import request_run_task_api
from utils.util.apscheduler import AsyncIOScheduler

job = FastAPI(
    docs_url=None,
    redoc_url=None,
    title="测试平台job",
    version="1.0.0",
    description='测试平台的任务管理'
)

# 注册钩子函数
register_app_hook(job)
register_request_hook(job)
register_exception_handler(job)

scheduler = AsyncIOScheduler()


@job.on_event('startup')
async def init_scheduler():
    """ 初始化定时任务 """
    await scheduler.init_scheduler()


@job.post("/api/job", summary="添加定时任务")
async def add_job(request: Request, task: dict = Body(), task_type: str = Body()):
    task_code = f'{task_type}_{str(task["id"])}'
    await scheduler.add_new_job(
        task_code=task_code,
        func=request_run_task_api,  # 异步执行任务
        kwargs={"task_code": task_code, "task_type": task_type, "skip_holiday": task.get("skip_holiday")},
        cron=task["cron"]
    )
    return request.app.success(f'定时任务启动成功')


@job.delete("/api/job", summary="删除定时任务")
async def add_job(form: GetJobForm, request: Request):
    await scheduler.remove_exist_job(form.task_code)  # 移除任务
    return request.app.success(f'任务禁用成功')


if __name__ == '__main__':
    import uvicorn

    uvicorn.run('job:job', host="0.0.0.0", port=job_server_port, workers=1)
