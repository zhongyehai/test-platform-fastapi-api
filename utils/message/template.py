from datetime import datetime

from app.enums import ReceiveTypeEnum


def inspection_ding_ding(content, kwargs):
    """ 巡检-钉钉报告模板 """
    # todo 消息加@  https://open.dingtalk.com/document/orgapp/custom-robots-send-group-messages
    case_stat, step_stat = content["stat"]["test_case"], content["stat"]["test_step"]
    pass_rate = round(case_stat["success"] / case_stat["total"] * 100, 3) if case_stat["total"] else 100
    return {
        "msgtype": "markdown",
        "markdown": {
            "title": "巡检通知",
            "text": f'### 巡检通知 {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} \n> '
                    f'#### 任务名: {kwargs["name"]} \n> '
                    f'#### 运行环境:<font color=#409EFF> {content["env"]["name"]} </font>\n> '
                    f'#### 执行用例:<font color=#409EFF> {case_stat["total"]} </font>条 \n> '
                    f'#### 成功:<font color=#00FF00> {case_stat["success"]} </font>条 \n> '
                    f'#### 失败:<font color=#FF0000> {case_stat["fail"]} </font>条 \n> '
                    f'#### 通过率:<font color=#409EFF> {pass_rate}% </font> \n> '
                    f'#### 此次共运行<font color=#19D4AE> {step_stat["total"]} </font>个步骤，'
                    f'涉及<font color=#19D4AE> {content["stat"]["count"]["api"]} </font>个接口 \n> '
                    f'#### 详情请登录[测试平台]({kwargs["report_addr"] + str(kwargs["report_id"])})查看\n'
        }
    }


def inspection_we_chat(content, kwargs):
    """ 巡检-企业微信报告模板 """
    # todo 消息加@ https://developer.work.weixin.qq.com/document/path/91770
    case_stat, step_stat = content["stat"]["test_case"], content["stat"]["test_step"]
    pass_rate = round(case_stat["success"] / case_stat["total"] * 100, 3) if case_stat["total"] else 100
    return {
        "msgtype": "markdown",
        "markdown": {
            "content": f'>巡检通知 {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n'
                       f'>任务名: {kwargs["name"]} \n'
                       f'>运行环境: {content["env"]["name"]} \n'
                       f'>执行用例:<font color="comment"> {case_stat["total"]} </font>条\n'
                       f'>成功:<font color="info"> {case_stat["success"]} </font>条\n'
                       f'>失败:<font color="warning"> {case_stat["fail"]} </font>条\n'
                       f'>通过率:<font color="warning"> {pass_rate}% </font>\n'
                       f'>此次共运行<font color=#info> {step_stat["total"]} </font>个步骤，'
                       f'涉及<font color=#info> {content["stat"]["count"]["api"]} </font>个接口 \n> '
                       f'详情请登录[测试平台]({kwargs["report_addr"] + str(kwargs["report_id"])})查看'
        }
    }


def get_inspection_msg(_type, content, kwargs):
    return inspection_ding_ding(content, kwargs) if _type == ReceiveTypeEnum.DING_DING else inspection_we_chat(content, kwargs)


def render_html_report(content, kwargs):
    """ 巡检-邮件模板 """
    case_stat, step_stat = content["stat"]["test_case"], content["stat"]["test_step"]
    pass_rate = round(case_stat["success"] / case_stat["total"] * 100, 3) if case_stat["total"] else 100
    msg = f"""
    <div>
        <h2>巡检通知：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</h2>
        <div><span>任务名: <span style="color: #60C0DDFF">{kwargs["name"]}</span></span></div>
        <div><span>运行环境: <span style="color: #60C0DDFF">{content["env"]["name"]}</span></span></div>
        <div><span>执行用例: <span style="color: #60C0DDFF">{case_stat["total"]}</span> 条</span></div>
        <div><span>成功: <span style="color: #9BCA63FF">{case_stat["success"]}</span> 条</span></div>
        <div><span>失败: <span style="color: #FA6E86FF">{case_stat["fail"]}</span> 条</span></div>
        <div><span>通过率: <span style="color: #60C0DDFF">{pass_rate}</span>%</span></div>
        <div>
            <span>
                此次共运行: 
                <span style="color: #60C0DDFF"> {step_stat["total"]} </span>
                个步骤, 涉及 
                <span style="color: #60C0DDFF"> {content["stat"]["count"]["api"]} </span> 
                个接口 
            </span>
        </div>
        <div>
            <span>详情请登录【<a style="color: #60C0DDFF" href="{kwargs["report_addr"] + str(kwargs["report_id"])}">测试平台</a>】查看</span>
        </div>
    </div>
    """

    return {"result": content["result"], "msg": msg}


def diff_api_msg(content, host, diff_api_addr, report_id):
    """ 接口对比报告模板 -- 钉钉 """
    return {
        "msgtype": "markdown",
        "markdown": {
            "title": "接口监控",
            "text": f'## 接口监控 {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} \n> '
                    f'### 任务名：{content["title"]} \n> '
                    f'#### 对比服务:<font color=#27AE60> {content["project"]["totle"]} </font>个 \n> '
                    f'##### 新增服务:<font color=#27AE60> {content["project"]["add"]} </font>个 \n> '
                    f'##### 修改服务:<font color=#3498DB> {content["project"]["modify"]} </font>个 \n> '
                    f'##### 删除服务:<font color=#E74C3C> {content["project"]["remove"]} </font>个 \n> '
                    f'##### 乱码:<font color=#E74C3C> {content["project"]["errorCode"]} </font>个 \n> '
                    f'##### \n> '
                    f'#### 对比模块:<font color=#27AE60> {content["module"]["totle"]} </font>个 \n> '
                    f'##### 新增模块:<font color=#27AE60> {content["module"]["add"]} </font>个 \n> '
                    f'##### 修改模块:<font color=#3498DB> {content["module"]["modify"]} </font>个 \n> '
                    f'##### 删除模块:<font color=#E74C3C> {content["module"]["remove"]} </font>个 \n> '
                    f'##### 乱码:<font color=#E74C3C> {content["module"]["errorCode"]} </font>个 \n> '
                    f'##### \n> '
                    f'#### 对比接口:<font color=#27AE60> {content["api"]["totle"]} </font>个 \n> '
                    f'##### 新增接口:<font color=#27AE60> {content["api"]["add"]} </font>个 \n> '
                    f'##### 修改接口:<font color=#3498DB> {content["api"]["modify"]} </font>个 \n> '
                    f'##### 删除接口:<font color=#E74C3C> {content["api"]["remove"]} </font>个 \n> '
                    f'##### 乱码:<font color=#E74C3C> {content["api"]["errorCode"]} </font>个 \n> '
                    f'##### \n> '
                    f'#### 请登录[测试平台]({host}{diff_api_addr}{str(report_id)})查看详情，并确认是否更新\n'
        }
    }


def run_time_error_msg(content, host, func_error_addr):
    """ 执行自定义函数时发生了异常的报告 -- 钉钉 """
    return {
        "msgtype": "markdown",
        "markdown": {
            "title": content.get("title"),
            "text": content.get("detail") + f"#### 详情请登录[测试平台]({host}{func_error_addr})查看\n"
        }
    }


def build_call_back_webhook_msg(data):
    """ 发送回调数据消息到即时通讯 -- 钉钉 """
    return {
        "msgtype": "markdown",
        "markdown": {
            "title": "测试平台回调",
            "text": data
        }
    }


def business_stage_count_ding_ding(content):
    """ 组装阶段统计报告
    content：{
              "countTime": "month",
              "total": 189,
              "pass": 163,
              "fail": 26,
              "passRate": 0.862,
              "hitRecord": {
                "代码问题": 5,
                "环境问题": 2
              },
              "webhookList": [
                "https://"
              ],
              "receiveType": "ding_ding",
              "record": [
                {
                  "total": 189,
                  "pass": 163,
                  "fail": 26,
                  "passRate": 0.862,
                  "record": [],
                  "hitRecord": {
                    "代码问题": 5,
                    "环境问题": 2
                  },
                  "name": "服务XXX"
                }
              ]
            }
    """
    msg_template = {
        "msgtype": "markdown",
        "markdown": {"title": "阶段统计", "text": ""}
    }

    def get_detail_msg(time_type, title, data):
        detail_template = f'\n' \
                          f'#### 【{title}】<font color=#409EFF>本{time_type}</font> ' \
                          f'共执行自动化测试: <font color=#409EFF>{data["total"]}</font> 次\n> ' \
                          f'#### 通过: <font color=#409EFF> {data["pass"]} </font>次\n> ' \
                          f'#### 失败: <font color=#409EFF> {data["fail"]} </font>次\n> ' \
                          f'#### 通过率为: <font color=#409EFF> {round(data["passRate"] * 100, 2)}% </font>\n> '

        # 汇总问题记录
        total_hit_count = 0
        # if data["hitRecord"]:  # 有问题记录才统计
        hit_record_total = '#### 其中\n> '
        for hit_title, hit_count in data["hitRecord"].items():
            total_hit_count += hit_count
            hit_record_total += f'#### {hit_title}: <font color=#FF0000>{hit_count}</font> 个\n>'
        hit_record_total = f'#### 共记录问题: <font color=#FF0000>{total_hit_count}</font> 个\n>' + hit_record_total
        detail_template += hit_record_total
        return detail_template

    count_type = "月" if content["countTime"] == "month" else "周"
    msg_template["markdown"]["title"] = f'{count_type}统计报告'

    # 业务线汇总
    builtins_msg = f'### <font color=#409EFF>自动化测试{count_type}统计报告</font>\n>' \
                   f'#### 统计时间 {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n>'
    builtins_msg += get_detail_msg(count_type, "本业务线", content)

    # 遍历每个服务
    for project in content["record"]:
        if project["total"]:  # 有执行的才统计
            builtins_msg += get_detail_msg(count_type, project["name"], project)

    msg_template["markdown"]["text"] = builtins_msg
    return msg_template


def business_stage_count_we_chat(content):
    pass


def get_business_stage_count_msg(content):
    if content["receiveType"] == "ding_ding":
        return business_stage_count_ding_ding(content)
    return business_stage_count_we_chat(content)
