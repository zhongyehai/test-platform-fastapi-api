""" apscheduler 默认的调度器存储对于异步支持有问题，这里自己实现存储，启动 """
from apscheduler.schedulers.asyncio import AsyncIOScheduler as _AsyncIOScheduler
from tortoise import Tortoise
from loguru import logger

from app.system.model_factory import ApschedulerJobs
from config import tortoise_orm_conf
from utils.parse.parse_cron import parse_cron
from utils.util.request import request_run_task_api


class AsyncIOScheduler(_AsyncIOScheduler):

    async def init_scheduler(self):
        """ 初始化scheduler，并把状态为要执行的任务添加到任务队列中 """
        await Tortoise.init(tortoise_orm_conf, timezone="Asia/Shanghai")  # 数据库链接

        logger.info("开始启动scheduler...")
        self.start()
        logger.info("scheduler启动成功...")

        logger.info("开始把【ApschedulerJobs】表中的任务添加到内存中...")
        task_list = await ApschedulerJobs.filter().all()  # 数据库中的所有任务
        for task in task_list:
            task_type, task_id = task.task_code.split("_", 1)

            await self.add_new_job(
                task_code=f'{task_type}_{task_id}',
                func=request_run_task_api,
                kwargs={"task_code": task.task_code, "task_type": task_type},
                cron=task.cron
            )

        logger.info("定时任务添加完成...")

    async def add_new_job(self, task_code, cron, *args, **kwargs):
        """ 添加任务 """
        kwargs.setdefault("trigger", "cron")
        kwargs.setdefault("misfire_grace_time", 60)
        kwargs.setdefault("coalesce", False)
        memory_job = self.add_job(*args, **kwargs, **parse_cron(cron))
        if await ApschedulerJobs.filter(task_code=task_code).first():
            await ApschedulerJobs.filter(task_code=task_code).update(job_id=memory_job.id)
        else:
            await ApschedulerJobs.create(
                task_code=task_code, cron=cron, next_run_time=memory_job.next_run_time, job_id=memory_job.id)

    async def remove_exist_job(self, job_code, *args, **kwargs):
        """ 移除任务 """
        if job := await ApschedulerJobs.filter(task_code=job_code).first():
            self.remove_job(job.job_id, *args, **kwargs)
            await ApschedulerJobs.filter(job_id=job.job_id).delete()

    # TODO 重写任务执行方法，把next_run_time更新到数据库
