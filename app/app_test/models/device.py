from app.baseModel import BaseModel, pydantic_model_creator, fields


class AppUiRunServer(BaseModel):
    """ 运行服务器表 """

    name = fields.CharField(255, null=True, unique=True, description="服务器名字")
    num = fields.IntField(null=True, description="序号")
    os = fields.CharField(8, null=True, description="服务器系统类型：windows/mac/linux")
    ip = fields.CharField(32, null=True, description="服务器ip地址")
    port = fields.CharField(8, null=True, default="4723", description="服务器端口号")
    status = fields.IntField(default=0, description="最近一次访问状态，0:未访问，1:访问失败，2:访问成功")

    class Meta:
        table = "app_ui_test_run_server"
        table_description = "APP测试运行服务器表"

    async def request_fail(self):
        await self.model_update({"status": 1})

    async def request_success(self):
        await self.model_update({"status": 2})


class AppUiRunPhone(BaseModel):
    """ 运行终端表 """

    name = fields.CharField(255, null=True, unique=True, description="设备名字")
    num = fields.IntField(null=True, description="序号")
    os = fields.CharField(8, null=True, description="设备系统类型：Android/ios")
    os_version = fields.CharField(255, null=True, description="设备系统版本号")
    device_id = fields.CharField(255, null=True, description="终端设备id")
    extends = fields.JSONField(default={}, description="设备扩展字段")
    screen = fields.CharField(64, null=True, description="屏幕分辨率")

    class Meta:
        table = "app_ui_test_run_phone"
        table_description = "APP测试运行终端表"


AppUiRunServerPydantic = pydantic_model_creator(AppUiRunServer, name="AppUiRunServer")
AppUiRunPhonePydantic = pydantic_model_creator(AppUiRunPhone, name="AppUiRunPhone")
