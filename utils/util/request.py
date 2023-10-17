import datetime

import httpx
from loguru import logger

from config import main_server_host
from app.config.model_factory import Config


async def request(url, *args, **kwargs):
    try:
        async with httpx.AsyncClient() as client:
            res = await client.request(url, **kwargs)
        return res
    except Exception as error:
        logger.error("发送请求出错")
        return {"status": 0, "msg": "发送请求出错", "data": error}


async def get(url, **kwargs):
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(url=url, headers=kwargs.get("headers", {}), params=kwargs.get("params", {}))
        return res
    except Exception as error:
        logger.error("发送请求出错")
        return {"status": 0, "msg": "发送请求出错", "data": error}


async def post(url, **kwargs):
    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(url, **kwargs)
        return res
    except Exception as error:
        logger.error("发送请求出错")
        return {"status": 0, "msg": "发送请求出错", "data": error}


async def put(url, **kwargs):
    return await request(url, method="PUT", **kwargs)


async def delete(url, **kwargs):
    try:
        async with httpx.AsyncClient() as client:
            # client.delete不支持json参数，所以直接调client.request
            res = await client.request(method="DELETE", url=url, headers=kwargs.pop("headers"), json=kwargs.pop("json"))
        return res
    except Exception as error:
        logger.error("发送请求出错")
        return {"status": 0, "msg": "发送请求出错", "data": error}


async def login():
    """ 登录 """
    response = await post(
        url=f'{main_server_host}/api/system/user/login',
        json={
            "account": "common",
            "password": "common"
        }
    )
    return {"X-Token": response.json()['data']['token']}


async def request_run_task_api(task_code, task_type, skip_holiday=True):
    """ 调执行任务接口 """
    logger.info(f'{"*" * 20} 开始触发执行定时任务 {"*" * 20}')

    # 判断是否设置了跳过节假日、调休日
    if skip_holiday:
        to_day = datetime.datetime.today().strftime("%Y-%m-%d")
        holiday_list = await Config.get_holiday_list()
        if to_day in holiday_list:
            return

    if isinstance(task_code, str) and task_code.startswith('cron'):  # 系统定时任务
        api_addr = '/system/job/run'
    else:  # 自动化测试定时任务
        api_addr = f'/{task_type}Test/task/run'

    task_type, task_id = task_code.split("_", 1)  # api_1  cron_cron_xx_
    response = await post(
        url=f'{main_server_host}/api{api_addr}',
        headers=await login(),
        json={
            "id": task_id,
            "func": task_id,
            "trigger_type": "cron"
        }
    )

    logger.info(f'{"*" * 20} 定时任务触发完毕 {"*" * 20}')
    logger.info(f'{"*" * 20} 触发响应为：{response.json()} {"*" * 20}')

    # TODO 更新next_run_time
    return response
