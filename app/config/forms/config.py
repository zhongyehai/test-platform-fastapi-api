import json
from typing import Optional
from pydantic import Field
from fastapi import Request
from selenium.webdriver.common.keys import Keys

from ...baseForm import BaseForm, PaginationForm
from ..model_factory import Config, ConfigType
from config import data_type_mapping, skip_if_type_mapping, run_model, extracts_mapping, assert_mapping_list, \
    http_method, api_suite_list, ui_suite_list, run_type, ui_assert_mapping_list, ui_extract_mapping_list, \
    ui_action_mapping_list, browser_name, app_key_board_code, server_os_mapping, phone_os_mapping, \
    make_user_info_mapping, make_user_language_mapping, test_type


class GetConfigTypeListForm(PaginationForm):
    """ 获取配置类型列表 """
    name: Optional[str] = Field(title="类型名")
    create_user: Optional[int] = Field(title="创建者")

    def get_query_filter(self, *args, **kwargs):
        """ 查询条件 """
        filter_dict = {}
        if self.name:
            filter_dict["name__icontains"] = self.name
        if self.create_user:
            filter_dict["create_user"] = int(self.create_user)
        return filter_dict


class GetConfigTypeForm(BaseForm):
    """ 配置类型id存在 """
    id: int = Field(..., title="配置类型id")

    async def validate_config_type_is_exist(self):
        return await self.validate_data_is_exist("配置类型不存在", ConfigType, id=self.id)

    async def validate_request(self, request: Request, *args, **kwargs):
        return await self.validate_config_type_is_exist()


class DeleteConfigTypeForm(GetConfigTypeForm):
    """ 删除配置类型表单校验 """

    async def validate_request(self, request: Request, *args, **kwargs):
        config_type = await self.validate_config_type_is_exist()
        await self.validate_data_is_not_exist('类型已被引用，不可删除', ConfigType, type=self.id)
        return config_type


class PostConfigTypeForm(BaseForm):
    """ 新增配置类型表单校验 """
    name: str = Field(..., title="类型名")
    desc: Optional[str] = Field(title="备注")

    async def validate_request(self, request: Request, *args, **kwargs):
        """ 数据值校验 """
        await self.validate_data_is_not_exist(f"配置类型 {self.name} 已存在", ConfigType, name=self.name)


class PutConfigTypeForm(GetConfigTypeForm, PostConfigTypeForm):
    """ 修改配置类型表单校验 """

    async def validate_request(self, request: Request, *args, **kwargs):
        """ 数据值校验 """
        config_type = await self.validate_config_type_is_exist()
        await self.validate_data_is_not_repeat(f"配置类型 {self.name} 已存在", ConfigType, self.id, name=self.name)
        return config_type


class FindConfigForm(PaginationForm):
    """ 查找配置form """
    type: Optional[str] = Field(title="配置类型")
    name: Optional[str] = Field(title="配置名")
    value: Optional[str] = Field(title="配置值")
    create_user: Optional[str] = Field(title="创建者")

    def get_query_filter(self, *args, **kwargs):
        """ 查询条件 """
        filter_dict = {}
        if self.type:
            filter_dict["type"] = int(self.type)
        if self.name:
            filter_dict["name__icontains"] = self.name
        if self.value:
            filter_dict["value__icontains"] = self.value
        if self.create_user:
            filter_dict["create_user"] = int(self.create_user)
        return filter_dict


class GetConfigForm(BaseForm):
    """ 获取配置 """

    id: Optional[int] = Field(title="配置id")
    code: Optional[str] = Field(title="配置名")

    async def validate_config_is_exist(self):
        if self.id:
            return await self.validate_data_is_exist(f"配置不存在", Config, id=self.id)
        return await self.validate_data_is_exist(f"配置不存在", Config, name=self.code)

    async def validate_request(self, request: Request, *args, **kwargs):
        # 获取配置
        match self.code:
            case "data_type_mapping":
                return data_type_mapping
            case "skip_if_type_mapping":
                return skip_if_type_mapping
            case "run_model":
                return run_model
            case "extracts_mapping":
                return extracts_mapping
            case "assert_mapping_list":
                return assert_mapping_list
            case "ui_assert_mapping_list":
                return ui_assert_mapping_list
            case "ui_extract_mapping_list":
                return ui_extract_mapping_list
            case "ui_action_mapping_list":
                return ui_action_mapping_list
            case "ui_key_board_code":
                return {key: f'按键【{key}】' for key in dir(Keys) if key.startswith('_') is False}
            case "app_key_board_code":
                return app_key_board_code
            case "http_method":
                return http_method
            case "api_suite_list":
                return api_suite_list
            case "ui_suite_list":
                return ui_suite_list
            case "run_type":
                return run_type
            case "browser_name":
                return browser_name
            case "server_os_mapping":
                return server_os_mapping
            case "phone_os_mapping":
                return phone_os_mapping
            case "make_user_info_mapping":
                return make_user_info_mapping
            case "make_user_language_mapping":
                return make_user_language_mapping
            case "test_type":
                return test_type

            case _:
                conf = await self.validate_config_is_exist()
                try:
                    return json.loads(conf.value)
                except:
                    return conf.value


class GetSkipIfConfigForm(BaseForm):
    """ 获取跳过类型配置 """

    test_type: str = Field(..., title="测试类型")
    type: str = Field(..., title="跳过类型")

    def validate_request(self, *args, **kwargs):
        data = [{"label": "运行环境", "value": "run_env"}]
        if self.test_type == "appUi":
            data += [{"label": "运行服务器", "value": "run_server"}, {"label": "运行设备", "value": "run_device"}]
        if self.type == "step":
            step_skip = [{"label": "自定义变量", "value": "variable"}, {"label": "自定义函数", "value": "func"}]
            return data + step_skip
        return data


class GetFindElementByForm(BaseForm):
    """ 获取定位方式数据源 """

    test_type: str = Field(..., title="测试类型")

    def validate_request(self, *args, **kwargs):
        data = [
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
        if self.test_type == "appUi":
            data += [
                {"label": "根据元素范围坐标定位", "value": "bounds"},
                {"label": "accessibility_id", "value": "accessibility id"}
            ]
        return data


class GetConfigByIdForm(BaseForm):
    """ 获取配置表单校验 """
    id: int = Field(..., title="配置id")

    async def validate_config_is_exist(self):
        return await self.validate_data_is_exist("配置不存在", Config, id=self.id)

    async def validate_request(self, request: Request, *args, **kwargs):
        return await self.validate_config_is_exist()


class DeleteConfigForm(GetConfigByIdForm):
    """ 删除配置表单校验 """


class PostConfigForm(BaseForm):
    """ 新增配置表单校验 """
    name: str = Field(..., title="配置名")
    value: str = Field(..., title="配置值")
    type: str = Field(..., title="配置类型")
    desc: Optional[str] = Field(title="备注")

    async def validate_request(self, request: Request, *args, **kwargs):
        await self.validate_data_is_not_exist(f"配置 {self.name} 已存在", Config, name=self.name)


class PutConfigForm(GetConfigByIdForm, PostConfigForm):
    """ 修改配置表单校验 """

    async def validate_request(self, request: Request, *args, **kwargs):
        config = await self.validate_config_is_exist()
        await self.validate_data_is_not_repeat(f"配置 {self.name} 已存在", Config, self.id, name=self.name)
        return config
