from app.baseModel import fields, pydantic_model_creator, BaseModel


class ConfigType(BaseModel):
    """ 配置类型表 """

    name = fields.CharField(128, null=True, unique=True, description="字段名")
    desc = fields.CharField(255, description="描述")

    class Meta:
        table = "config_type"
        table_description = "配置类型表"


class Config(BaseModel):
    """ 配置表 """

    name = fields.CharField(128, null=True, index=True, unique=True, description="字段名")
    value = fields.TextField(null=True, description="字段值")
    type = fields.IntField(null=True, index=True, description="配置类型")
    desc = fields.TextField(description="描述")

    class Meta:
        table = "config_config"
        table_description = "配置表"

    @classmethod
    async def get_config(cls, name: str):
        """ 获取配置 """
        data = await cls.filter(name=name).first()
        return data.value

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
        return await cls.get_config("kym")

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
    async def get_appium_new_command_timeout(cls):
        return await cls.get_config("appium_new_command_timeout")

    @classmethod
    async def get_holiday_list(cls):
        return cls.loads(await cls.get_config("holiday_list"))

    @classmethod
    async def get_find_element_option(cls):
        return cls.loads(await cls.get_config(name="find_element_option"))

    # @classmethod
    # def get_default_diff_message_send_addr(cls):
    #     """ 配置的对比结果通知地址 """
    #     return cls.get_first(name="default_diff_message_send_addr").value
    #
    # @classmethod
    # def get_callback_webhook(cls):
    #     return cls.get_first(name="callback_webhook").value
    #
    # @classmethod
    # def get_call_back_response(cls):
    #     return cls.get_first(name="call_back_response").value
    #
    # @classmethod
    # def get_data_source_callback_addr(cls):
    #     return cls.get_first(name="data_source_callback_addr").value
    #
    # @classmethod
    # def get_data_source_callback_token(cls):
    #     return cls.get_first(name="data_source_callback_token").value
    #
    #
    # @classmethod
    # def get_pagination_size(cls):
    #     return cls.loads(cls.get_first(name="pagination_size").value)
    #
    # @classmethod
    # def get_ui_report_addr(cls):
    #     return cls.get_first(name="ui_report_addr").value
    #
    # @classmethod
    # def get_run_type(cls):
    #     return cls.loads(cls.get_first(name="run_type").value)
    #
    # @classmethod
    # def get_sync_mock_data(cls):
    #     return cls.loads(cls.get_first(name="sync_mock_data").value)


ConfigTypePydantic = pydantic_model_creator(ConfigType, name="ConfigType")
ConfigPydantic = pydantic_model_creator(Config, name="Config")
