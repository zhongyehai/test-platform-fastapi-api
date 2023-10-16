# -*- coding: utf-8 -*-
from datetime import datetime
from threading import Thread

from loguru import logger
import requests

from app.enums import SendReportTypeEnum, ReceiveTypeEnum
from utils.message.send_email import SendEmail
from utils.message.template import diff_api_msg, run_time_error_msg, build_call_back_webhook_msg, render_html_report, \
    get_inspection_msg, get_business_stage_count_msg
from app.config.model_factory import Config
from app.assist.model_factory import CallBack
from config import error_push, default_web_hook


def send_msg(addr, msg):
    """ 发送消息 """
    logger.info(f'发送消息：{msg}')
    try:
        logger.info(f'发送消息结果：{requests.post(addr, json=msg, verify=False).json()}')
    except Exception as error:
        logger.error(f'向机器人发送测试报告失败，错误信息：\n{error}')


def send_server_status(server_name, app_title=None, action_type="启动"):
    """ 服务启动/关闭成功 """
    msg = {
        "msgtype": "markdown",
        "markdown": {
            "title": f"服务{action_type}通知",
            "text": f'### 服务{action_type}通知 {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} \n> '
                    f'#### 服务<font color=#FF0000>【{server_name}】【{app_title}】</font>{action_type}完成 \n> '
        }
    }
    send_msg(default_web_hook, msg)


def send_inspection_by_msg(receive_type, content, kwargs):
    """ 发送巡检消息 """
    msg = get_inspection_msg(receive_type, content, kwargs)
    for webhook in kwargs["webhook_list"]:
        if webhook:
            send_msg(webhook, msg)


def send_inspection_by_email(content, kwargs):
    """ 通过邮件发送测试报告 """
    SendEmail(
        kwargs.get("email_server"),
        kwargs.get("email_from").strip(),
        kwargs.get("email_pwd"),
        [email.strip() for email in kwargs.get("email_to") if email],
        render_html_report(content, kwargs)
    ).send_email()


def send_report(**kwargs):
    """ 封装发送测试报告提供给多线程使用 """
    logger.info(f'开始发送测试报告')
    is_send, receive_type, content = kwargs.get("is_send"), kwargs.get("receive_type"), kwargs.get("content")
    if is_send == SendReportTypeEnum.ALWAYS or (is_send == SendReportTypeEnum.ON_FAIL and content["result"] != "success"):
        if receive_type == ReceiveTypeEnum.EMAIL:
            send_inspection_by_email(content, kwargs)
        else:
            send_inspection_by_msg(receive_type, content, kwargs)
    logger.info(f'测试报告发送完毕')

# def async_send_report(**kwargs):
#     """ 多线程发送测试报告 """
#     logger.info(f'开始多线程发送测试报告')
#     Thread(target=send_report, kwargs=kwargs).start()
#     logger.info(f'多线程发送测试报告完毕')


async def call_back_for_pipeline(task_id, call_back_info: list, extend: dict, status):
    """ 把测试结果回调给流水线 """
    for call_back in call_back_info:
        logger.info(f'开始回调流水线：{call_back.get("url")}')
        call_back.get('json', {})["status"] = status
        call_back.get('json', {})["taskId"] = task_id
        call_back.get('json', {})["extend"] = extend

        call_back_obj = await CallBack.create(**{
            "ip": None,
            "url": call_back.get("url", None),
            "method": call_back.get("method", None),
            "headers": call_back.get("headers", {}),
            "params": call_back.get("args", {}),
            "data_form": call_back.get("form", {}),
            "data_json": call_back.get("json", {}),
        })

        try:
            call_back_res = requests.request(**call_back).text
            await call_back_obj.success(call_back_res)
            logger.info(f'回调流水线：{call_back.get("url")}结束: \n{call_back_res}')
            msg = build_call_back_webhook_msg(call_back.get("json", {}))
            send_msg(await Config.get_call_back_msg_addr(), msg)
        except Exception as error:
            logger.error(f'回调流水线：{call_back.get("url")}失败')
            await call_back_obj.fail()
            # 发送即时通讯通知
            try:
                requests.post(
                    url=error_push.get("url"),
                    json={
                        "key": error_push.get("key"),
                        "head": f'回调{call_back.get("url")}报错了',
                        "body": f'{error}'
                    }
                )
            except Exception as error:
                logger.error("发送回调流水线错误消息失败")
    logger.info("回调流水线执行结束")


async def send_diff_api_message(content, report_id, addr):
    """ 发送接口对比报告 """
    msg = diff_api_msg(content, await Config.get_report_host(), await Config.get_diff_api_addr(), report_id)
    send_msg(addr, msg)


async def send_run_time_error_message(content, addr):
    """ 执行自定义函数时发生了异常的报告 """
    msg = run_time_error_msg(content, await Config.get_report_host(), await Config.get_func_error_addr())
    send_msg(addr, msg)


def async_send_run_time_error_message(**kwargs):
    """ 多线程发送错误信息 """
    logger.info("开始多线程发送错误信息")
    Thread(target=send_run_time_error_message, kwargs=kwargs).start()
    logger.info("多线程发送错误信息完毕")


async def send_run_func_error_message(content):
    """ 运行自定义函数错误通知 """
    async_send_run_time_error_message(
        content=content,
        addr=f'{await Config.get_report_host()}{await Config.get_run_time_error_message_send_addr()}'
    )


def send_business_stage_count(content):
    """ 发送阶段统计报告 """
    # if content["total"]:
    msg = get_business_stage_count_msg(content)
    for webhook in content["webhookList"]:
        send_msg(webhook, msg)


if __name__ == "__main__":
    pass
