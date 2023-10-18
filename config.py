import os
import platform

from utils.client.test_runner import validate_func as assert_func_file
from utils.client.test_runner.webdriver_action import Actions

is_linux = platform.platform().startswith("Linux")
basedir = os.path.abspath(".")
default_web_hook = ""  # 接收系统级别通知、错误信息的默认渠道

token_secret_key = "123qwe"  # 生成token的加密字符串
token_time_out = 12 * 60 * 60  # token有效时间，12个小时
hash_secret_key = "123qwe"  # 密码加密的字符串，一旦生成用户，不可更改，否则两次加密密文会不一致

main_server_port = 8024  # 主程序端口
main_server_host = f'http://localhost:{main_server_port}'  # 主程序后端服务

job_server_port = 8025  # job服务端口
job_server_host = f'http://localhost:{job_server_port}/api/job'  # job服务接口

# 从 testRunner.built_in 中获取断言方式并映射为字典和列表，分别给前端和运行测试用例时反射断言
assert_mapping, assert_mapping_list = {}, []
for func in dir(assert_func_file):
    if func.startswith("_") and not func.startswith("__"):
        doc = getattr(assert_func_file, func).__doc__.strip()  # 函数注释
        assert_mapping.setdefault(doc, func)
        assert_mapping_list.append({"value": doc})

# UI自动化的行为事件
action_mapping = Actions.get_action_mapping()
ui_action_mapping_dict, ui_action_mapping_list = action_mapping["mapping_dict"], action_mapping["mapping_list"]
ui_action_mapping_reverse = dict(zip(ui_action_mapping_dict.values(), ui_action_mapping_dict.keys()))

# UI自动化的断言事件
ui_assert_mapping = Actions.get_assert_mapping()
ui_assert_mapping_dict, ui_assert_mapping_list = ui_assert_mapping["mapping_dict"], ui_assert_mapping["mapping_list"]

# UI自动化的数据提取事件
extract_mapping = Actions.get_extract_mapping()
ui_extract_mapping, ui_extract_mapping_list = extract_mapping["mapping_dict"], extract_mapping["mapping_list"]
ui_extract_mapping.setdefault("自定义函数", "func")
ui_extract_mapping_list.extend([
    {"label": "常量", "value": "const"},
    {"label": "自定义变量", "value": "variable"},
    {"label": "自定义函数", "value": "func"}
])

# 跳过条件判断类型映射
skip_if_type_mapping = [
    {"label": "且", "value": "and"},
    {"label": "或", "value": "or"}
]

# 测试类型
test_type = [
    {"key": "api", "label": "接口测试"},
    {"key": "appUi", "label": "app测试"},
    {"key": "webUi", "label": "ui测试"}
]

# 运行测试的类型
run_type = {
    "api": "接口",
    "case": "用例",
    "suite": "用例集",
    "task": "任务",
}

# 执行模式
run_model = {0: "串行执行", 1: "并行执行"}

# 请求方法
http_method = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]

# 创建项目/服务时，默认要同时创建的用例集列表
api_suite_list = [
    {"key": "base", "value": "基础用例集"},
    {"key": "quote", "value": "引用用例集"},
    {"key": "api", "value": "单接口用例集"},
    {"key": "process", "value": "流程用例集"},
    {"key": "make_data", "value": "造数据用例集"}
]

ui_suite_list = [
    {"key": "base", "value": "基础用例集"},
    {"key": "quote", "value": "引用用例集"},
    {"key": "process", "value": "流程用例集"},
    {"key": "make_data", "value": "造数据用例集"}
]

# 数据提取类型
extracts_mapping = [
    {"label": "响应体", "value": "content"},
    {"label": "响应头部信息", "value": "headers"},
    {"label": "响应cookies", "value": "cookies"},
    {"label": "正则表达式（从响应体提取）", "value": "regexp"},
    {"label": "常量", "value": "const"},
    {"label": "自定义变量", "value": "variable"},
    {"label": "自定义函数", "value": "func"},
    {"label": "其他（常量、自定义变量、自定义函数）", "value": "other"}
]

# python数据类型
data_type_mapping = [
    {"label": "普通字符串", "value": "str"},
    {"label": "json字符串", "value": "json"},
    {"label": "整数", "value": "int"},
    {"label": "小数", "value": "float"},
    {"label": "列表", "value": "list"},
    {"label": "字典", "value": "dict"},
    {"label": "布尔值True", "value": "true"},
    {"label": "布尔值False", "value": "false"},
    {"label": "自定义函数", "value": "func"},
    {"label": "自定义变量", "value": "variable"}
]

# ui自动化支持的浏览器
browser_name = {
    "chrome": "chrome",
    "gecko": "火狐"
}

# 运行app自动化的服务器设备系统映射
server_os_mapping = ["Windows", "Mac", "Linux"]

# 运行app自动化的手机设备系统映射
phone_os_mapping = ["Android", "iOS"]

# APP模拟键盘输入的code
app_key_board_code = {
    "7": "按键'0'",
    "8": "按键'1'",
    "9": "按键'2'",
    "10": "按键'3'",
    "11": "按键'4'",
    "12": "按键'5'",
    "13": "按键'6'",
    "14": "按键'7'",
    "15": "按键'8'",
    "16": "按键'9'",
    "29": "按键'A'",
    "30": "按键'B'",
    "31": "按键'C'",
    "32": "按键'D'",
    "33": "按键'E'",
    "34": "按键'F'",
    "35": "按键'G'",
    "36": "按键'H'",
    "37": "按键'I'",
    "38": "按键'J'",
    "39": "按键'K'",
    "40": "按键'L'",
    "41": "按键'M'",
    "42": "按键'N'",
    "43": "按键'O'",
    "44": "按键'P'",
    "45": "按键'Q'",
    "46": "按键'R'",
    "47": "按键'S'",
    "48": "按键'T'",
    "49": "按键'U'",
    "50": "按键'V'",
    "51": "按键'W'",
    "52": "按键'X'",
    "53": "按键'Y'",
    "54": "按键'Z'",
    "4": "返回键",
    "5": "拨号键",
    "6": "挂机键",
    "82": "菜单键",
    "3": "home键",
    "27": "拍照键"
}

# faker 造数据方法映射
make_user_info_mapping = {
    "name": "姓名",
    "ssn": "身份证号",
    "phone_number": "手机号",
    "credit_card_number": "银行卡",
    "address": "地址",
    "company": "公司名",
    "credit_code": "统一社会信用代码",
    "company_email": "公司邮箱",
    "job": "工作",
    "ipv4": "ipv4地址",
    "ipv6": "ipv6地址"
}

# faker 造数据语言映射
make_user_language_mapping = {
    'zh_CN': '简体中文',
    'en_US': '英语-美国',
    'ja_JP': '日语-日本',
    'hi_IN': '印地语-印度',
    'ko_KR': '朝鲜语-韩国',
    'es_ES': '西班牙语-西班牙',
    'pt_PT': '葡萄牙语-葡萄牙',
    'es_MX': '西班牙语-墨西哥',
    # 'ar_EG': '阿拉伯语-埃及',
    # 'ar_PS': '阿拉伯语-巴勒斯坦',
    # 'ar_SA': '阿拉伯语-沙特阿拉伯',
    # 'bg_BG': '保加利亚语-保加利亚',
    # 'cs_CZ': '捷克语-捷克',
    # 'de_DE': '德语-德国',
    # 'dk_DK': '丹麦语-丹麦',
    # 'el_GR': '希腊语-希腊',
    # 'en_AU': '英语-澳大利亚',
    # 'en_CA': '英语-加拿大',
    # 'en_GB': '英语-英国',
    # 'et_EE': '爱沙尼亚语-爱沙尼亚',
    # 'fa_IR': '波斯语-伊朗',
    # 'fi_FI': '芬兰语-芬兰',
    # 'fr_FR': '法语-法国',
    # 'hr_HR': '克罗地亚语-克罗地亚',
    # 'hu_HU': '匈牙利语-匈牙利',
    # 'hy_AM': '亚美尼亚语-亚美尼亚',
    # 'it_IT': '意大利语-意大利',
    # 'ka_GE': '格鲁吉亚语-格鲁吉亚',
    # 'lt_LT': '立陶宛语-立陶宛',
    # 'lv_LV': '拉脱维亚语-拉脱维亚',
    # 'ne_NP': '尼泊尔语-尼泊尔',
    # 'nl_NL': '德语-荷兰',
    # 'no_NO': '挪威语-挪威',
    # 'pl_PL': '波兰语-波兰',
    # 'pt_BR': '葡萄牙语-巴西',
    # 'ru_RU': '俄语-俄国',
    # 'sl_SI': '斯诺文尼亚语-斯诺文尼亚',
    # 'sv_SE': '瑞典语-瑞典',
    # 'tr_TR': '土耳其语-土耳其',
    # 'uk_UA': '乌克兰语-乌克兰',
    # 'zh_TW': '繁体中文'
}

# tortoise-orm 配置
tortoise_orm_conf = {
    'connections': {
        'default': {
            # 连接字符串的形式特殊符号（#）会被解析为分隔符，所以用指定参数的形式
            'engine': 'tortoise.backends.mysql',
            'credentials': {
                'host': '',
                'port': '',
                'user': '',
                'password': '',
                'database': ''
            }

        }
    },
    'apps': {
        'test_platform': {
            'models': [
                "aerich.models",  # 数据库迁移要用
                'app.api_test.model_factory',
                'app.ui_test.model_factory',
                'app.app_test.model_factory',
                'app.system.model_factory',
                'app.config.model_factory',
                'app.assist.model_factory',
                'app.test_work.model_factory',
            ],
            "default_connection": "default",  # 数据库迁移会用到
        }
    },
    "timezone": "Asia/Shanghai"
}
