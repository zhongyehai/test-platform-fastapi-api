# -*- coding: utf-8 -*-
from datetime import datetime
from threading import Thread

import httpx

from app.models.config.model_factory import Config, WebHook
from app.models.assist.model_factory import CallBack
from app.schemas.enums import SendReportTypeEnum, ReceiveTypeEnum
from .send_email import SendEmail
from .template import run_time_error_msg, call_back_webhook_msg, render_html_report, \
    get_business_stage_count_msg, inspection_ding_ding, inspection_we_chat
from ..logs.log import logger
from config import _default_web_hook_type, _default_web_hook, _web_hook_secret


async def send_msg(addr, msg):
    """ 发送消息 """
    logger.info(f'发送消息，文本：{msg}')
    try:
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.post(addr, json=msg, timeout=30)
            logger.info(f'发送消息，结果：{response.json()}')
        return True
    except Exception as error:
        logger.info(f'向机器人发送测试报告失败，错误信息：\n{error}')
        return False


async def send_server_status(server_name, app_title=None, action_type="启动"):
    """ 服务启动/关闭成功 """
    msg = {
        "msgtype": "markdown",
        "markdown": {
            "title": f"服务{action_type}通知",
            "text": f'### 服务{action_type}通知 {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} \n> '
                    f'#### 服务<font color=#FF0000>【{server_name}】【{app_title}】</font>{action_type}完成 \n> '
        }
    }
    await send_msg(WebHook.build_webhook_addr(_default_web_hook_type, _default_web_hook, _web_hook_secret), msg)


async def send_system_error(title, content):
    """ 系统报错 """
    msg = {
        "msgtype": "text",
        "text": {
            "content": f"{title}:\n\n{content}"
        }
    }
    await send_msg(WebHook.build_webhook_addr(_default_web_hook_type, _default_web_hook, _web_hook_secret), msg)


async def send_inspection_by_msg(receive_type, content_list, kwargs):
    """ 发送巡检消息 """
    msg = inspection_ding_ding(content_list, kwargs) \
        if receive_type == ReceiveTypeEnum.DING_DING.value else inspection_we_chat(content_list, kwargs)
    res_list = [await send_msg(webhook, msg) for webhook in kwargs["webhook_list"]]
    return False not in res_list


def send_inspection_by_email(content_list, kwargs):
    """ 通过邮件发送测试报告 """
    return SendEmail(
        kwargs.get("email_server"),
        kwargs.get("email_from").strip(),
        kwargs.get("email_pwd"),
        [email.strip() for email in kwargs.get("email_to") if email],
        render_html_report(content_list, kwargs)
    ).send_email()


async def send_report(**kwargs):
    """ 发送测试报告 """
    is_send, receive_type, content_list = kwargs.get("is_send"), kwargs.get("receive_type"), kwargs.get("content_list")
    result = [content_data["report_summary"]["result"] for content_data in content_list]
    if is_send == SendReportTypeEnum.ALWAYS.value or (is_send == SendReportTypeEnum.ON_FAIL.value and "fail" in result):
        logger.info(f'开始发送测试报告')
        if receive_type == ReceiveTypeEnum.EMAIL.value:
            return send_inspection_by_email(content_list, kwargs)
            # Thread(target=send_inspection_by_email, args=[content_list, kwargs]).start()
        else:
            return await send_inspection_by_msg(receive_type, content_list, kwargs)
    return True

async def call_back_for_pipeline(task_id, call_back_info: list, extend: dict, status):
    """ 把测试结果回调给流水线 """
    logger.info("开始执行回调")
    for call_back in call_back_info:
        logger.info(f'开始回调{call_back.get("url")}')
        call_back.get('json', {})["status"] = status
        call_back.get('json', {})["taskId"] = task_id
        call_back.get('json', {})["extend"] = extend

        call_back_obj = await CallBack.model_create({
            "ip": None,
            "url": call_back.get("url", None),
            "method": call_back.get("method", None),
            "headers": call_back.get("headers", {}),
            "params": call_back.get("args", {}),
            "data_form": call_back.get("form", {}),
            "data_json": call_back.get("json", {}),
        })

        try:
            async with httpx.AsyncClient(verify=False) as client:
                response = await client.request(**call_back)
                logger.info(f'发送消息，结果：{response.json()}')
            call_back_obj.success(response.text)
            logger.info(f'回调{call_back.get("url")}结束: \n{response.text}')
            msg = call_back_webhook_msg(call_back.get("json", {}))
            await send_msg(await Config.get_call_back_msg_addr(), msg)
        except Exception as error:
            logger.info(f'回调{call_back.get("url")}失败')
            call_back_obj.fail()
            await send_system_error(title="回调报错通知", content=f'{error}')  # 发送通知
    logger.info("回调执行结束")


# async def send_run_time_error_message(content):
#     """ 执行自定义函数时发生了异常的报告 """
#     msg = run_time_error_msg(content, await Config.get_report_host(), await Config.get_func_error_addr())
#     await send_msg(WebHook.build_webhook_addr(_default_web_hook_type, _default_web_hook, _web_hook_secret), msg)


# async def send_run_func_error_message(content):
#     """ 运行自定义函数错误通知 """
#     logger.info("开始发送错误信息")
#     await send_run_time_error_message(content=content)
#     logger.info("错误信息发送完毕")


async def send_business_stage_count(content):
    """ 发送阶段统计报告 """
    # if content["total"]:
    msg = get_business_stage_count_msg(content)
    for webhook in content["webhookList"]:
        await send_msg(webhook, msg)


if __name__ == "__main__":
    pass
