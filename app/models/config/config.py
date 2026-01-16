from selenium.webdriver.common.keys import Keys

from ..base_model import fields, pydantic_model_creator, NumFiled
import config

class ConfigType(NumFiled):
    """ 配置类型表 """

    name = fields.CharField(128, null=True, unique=True, description="字段名")
    desc = fields.CharField(255, description="描述")

    class Meta:
        table = "config_type"
        table_description = "配置类型表"


class Config(NumFiled):
    """ 配置表 """

    name = fields.CharField(128, null=True, index=True, unique=True, description="字段名")
    value = fields.TextField(null=True, description="字段值")
    type = fields.IntField(null=True, index=True, description="配置类型")
    desc = fields.TextField(null=True, description="描述")

    class Meta:
        table = "config_config"
        table_description = "配置表"

    @classmethod
    async def get_config(cls, name: str):
        """ 获取配置 """
        data = await cls.filter(name=name).first().values("value")
        return data["value"]

    @classmethod
    async def get_pip_command(cls):
        """ 获取pip_command配置项 """
        return await cls.get_config("pip_command")

    @classmethod
    async def get_report_host(cls):
        return await cls.get_config("report_host")

    @classmethod
    async def get_api_report_addr(cls):
        return await cls.get_config("api_report_addr")

    @classmethod
    async def get_web_ui_report_addr(cls):
        return await cls.get_config("web_ui_report_addr")

    @classmethod
    async def get_app_ui_report_addr(cls):
        return await cls.get_config("app_ui_report_addr")

    @classmethod
    async def get_kym(cls):
        """ 获取kym配置项 """
        return cls.loads(await cls.get_config("kym"))

    @classmethod
    async def get_save_func_permissions(cls):
        return await cls.get_config("save_func_permissions")

    @classmethod
    async def get_call_back_msg_addr(cls):
        return await cls.get_config("call_back_msg_addr")

    @classmethod
    async def get_func_error_addr(cls):
        return await cls.get_config("func_error_addr")

    @classmethod
    async def get_diff_api_addr(cls):
        return await cls.get_config("diff_api_addr")

    @classmethod
    async def get_run_time_error_message_send_addr(cls):
        return await cls.get_config("run_time_error_message_send_addr")

    @classmethod
    async def get_request_time_out(cls):
        return await cls.get_config("request_time_out")

    @classmethod
    async def get_pause_step_time_out(cls):
        return int(await cls.get_config("pause_step_time_out"))

    @classmethod
    async def get_response_time_level(cls):
        return cls.loads(await cls.get_config("response_time_level"))

    @classmethod
    async def get_wait_time_out(cls):
        return await cls.get_config("wait_time_out")

    @classmethod
    async def get_appium_new_command_timeout(cls):
        return await cls.get_config("appium_new_command_timeout")

    @classmethod
    async def get_holiday_list(cls):
        return cls.loads(await cls.get_config("holiday_list"))

    @classmethod
    async def get_shell_command_info(cls):
        """ 获取sell造数据的配置项 """
        return cls.loads(await cls.get_config("shell_command_info"))

    @classmethod
    async def get_find_element_by_ui(cls):
        return [
        {"label": "根据id属性定位", "value": "id"},
        {"label": "根据xpath表达式定位", "value": "xpath"},
        {"label": "根据class选择器定位", "value": "class name"},
        {"label": "根据css选择器定位", "value": "css selector"},
        {"label": "根据name属性定位", "value": "name"},
        {"label": "根据tag名字定位 ", "value": "tag name"},
        {"label": "根据超链接文本定位", "value": "link text"},
        {"label": "页面地址", "value": "url"},
        {"label": "根据具体坐标定位", "value": "coordinate"}
    ]

    @classmethod
    async def get_find_element_by_app(cls):
        data = await cls.get_find_element_by_ui()
        data.extend([
            {"label": "根据元素范围坐标定位", "value": "bounds"},
            {"label": "accessibility_id", "value": "accessibility id"}
        ])
        return data

    @classmethod
    async def get_config_detail(cls, conf_id=None, conf_code=None):
        """ 先从 config.py 中找，没找到就从数据库查 """
        if conf_code and hasattr(config, conf_code):
            return getattr(config, conf_code)
        elif conf_code == "ui_key_board_code":
            return {key: f'按键【{key}】' for key in dir(Keys) if key.startswith('_') is False}
        else:
            if conf_id:
                conf = await Config.validate_is_exist("配置不存在", id=conf_id)
            else:
                conf = await Config.validate_is_exist("配置不存在", name=conf_code)
            try:
                return cls.loads(conf.value)
            except:
                return conf.value


ConfigTypePydantic = pydantic_model_creator(ConfigType, name="ConfigType")
ConfigPydantic = pydantic_model_creator(Config, name="Config")
