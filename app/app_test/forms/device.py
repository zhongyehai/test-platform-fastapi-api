from typing import Optional

import validators
from pydantic import Field

from ...baseForm import BaseForm, PaginationForm
from ..model_factory import AppUiRunServer as Server, AppUiRunPhone as Phone


class GetServerListForm(PaginationForm):
    """ 获取服务器列表 """
    name: Optional[str] = Field(title="服务器名")
    os: Optional[str] = Field(title="服务器系统类型")
    ip: Optional[str] = Field(title="服务器ip")
    port: Optional[str] = Field(title="服务器端口")

    def get_query_filter(self, *args, **kwargs):
        """ 查询条件 """
        filter_dict = {}
        if self.name:
            filter_dict["name__icontains"] = self.name
        if self.os:
            filter_dict["os"] = self.os
        if self.ip:
            filter_dict["ip"] = self.ip
        if self.port:
            filter_dict["port"] = self.port

        return filter_dict


class GetServerForm(BaseForm):
    """ 校验服务器id已存在 """
    id: int = Field(..., title="服务器id")

    async def validate_server_is_exist(self):
        return await self.validate_data_is_exist("服务器不存在", Server, id=self.id)

    async def validate_request(self, *args, **kwargs):
        return await self.validate_server_is_exist()


class AddServerForm(BaseForm):
    """ 添加服务器的校验 """

    name: str = Field(..., title="服务器名字")
    os: str = Field(..., title="服务器系统类型")
    ip: str = Field(..., title="服务器ip地址")
    port: str = Field(..., title="服务器端口")

    async def validate_request(self, *args, **kwargs):
        # 校验ip格式
        self.validate_is_true('服务器ip地址请去除协议标识', self.ip.lower().startswith(('http', 'https')) is False)
        self.validate_is_true("服务器ip地址错误", validators.ipv4(self.ip) or validators.ipv6(self.ip))


class EditServerForm(GetServerForm, AddServerForm):
    """ 修改服务器的校验 """

    async def validate_request(self, *args, **kwargs):
        return await self.validate_server_is_exist()


class GetPhoneListForm(PaginationForm):
    """ 获取运行设备列表 """

    name: Optional[str] = Field(title="运行设备名")
    os: Optional[str] = Field(title="运行设备系统类型")
    os_version: Optional[str] = Field(title="运行设备系统版本")

    def get_query_filter(self, *args, **kwargs):
        """ 查询条件 """
        filter_dict = {}
        if self.name:
            filter_dict["name__icontains"] = self.name
        if self.os:
            filter_dict["os"] = self.os
        if self.os_version:
            filter_dict["os_version__icontains"] = self.os_version

        return filter_dict


class GetPhoneForm(BaseForm):
    """ 获取运行设备 """
    id: int = Field(..., title="运行设备id")

    async def validate_phone_is_exist(self):
        return await self.validate_data_is_exist("运行设备不存在", Phone, id=self.id)

    async def validate_request(self, *args, **kwargs):
        return await self.validate_phone_is_exist()


class AddPhoneForm(BaseForm):
    """ 添加手机的校验 """

    name: str = Field(..., title="运行设备名字")
    os: str = Field(..., title="运行设备系统类型")
    os_version: str = Field(..., title="运行设备系统版本")
    device_id: str = Field(..., title="运行设备设备id")
    screen: str = Field(..., title="运行设备系统分辨率")
    extends: dict = Field(..., title="运行设备扩展信息")

    async def validate_request(self, *args, **kwargs):
        self.validate_is_true(f"分辨率格式错误", len(self.screen.lower().split('x')) == 2)


class EditPhoneForm(GetPhoneForm, AddPhoneForm):
    """ 修改手机的校验 """

    async def validate_request(self, *args, **kwargs):
        return await self.validate_phone_is_exist()
