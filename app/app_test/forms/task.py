from typing import Optional, Union
from pydantic import Field
from crontab import CronTab

from ...baseForm import BaseForm, PaginationForm
from ..model_factory import AppUiTask as Task, AppUiRunServer as Server, AppUiRunPhone as Phone
from ...enums import SendReportTypeEnum, ReceiveTypeEnum, TriggerTypeEnum


class GetTaskListForm(PaginationForm):
    """ 获取任务列表 """
    project_id: int = Field(..., title="服务id")

    def get_query_filter(self, *args, **kwargs):
        """ 查询条件 """
        return {"project_id": self.project_id}


class GetTaskForm(BaseForm):
    """ 校验任务id已存在 """
    id: int = Field(..., title="任务id")

    async def validate_task_is_exist(self):
        return await self.validate_data_is_exist("任务不存在", Task, id=self.id)

    async def validate_request(self, *args, **kwargs):
        return await self.validate_task_is_exist()


class DeleteTaskForm(GetTaskForm):
    """ 删除任务 """

    async def validate_request(self, *args, **kwargs):
        task = await self.validate_task_is_exist()
        self.validate_is_true(f"请先禁用任务", task.is_disable())
        return task


class RunTaskForm(GetTaskForm):
    """ 运行任务 """
    is_async: int = Field(default=0, title="任务的运行机制", description="0：串行，1：并行，默认0")
    env_list: Optional[list] = Field(title="运行环境")
    trigger_type: Optional[TriggerTypeEnum] = Field(
        TriggerTypeEnum.PAGE, title="触发类型", description="pipeline/page/cron")  # pipeline 跑完过后会发送测试报告
    extend: Optional[Union[list, dict, str]] = Field(title="运维传过来的扩展字段，接收的什么就返回什么")
    no_reset: bool = Field(default=False, title="是否不重置手机")
    server_id: int = Field(..., title="执行服务器")
    phone_id: int = Field(..., title="执行手机")

    async def validate_request(self, *args, **kwargs):
        task = await self.validate_task_is_exist()
        server = await self.validate_data_is_exist("服务器不存在", Server, id=self.server_id)  # 校验服务id存在
        await self.validate_appium_server_is_running(server.ip, server.port)  # 校验appium是否能访问
        phone = await self.validate_data_is_exist("手机不存在", Phone, id=self.phone_id)  # 校验手机id存在
        return {"task": task, "server": server, "phone": phone}


class AddTaskForm(BaseForm):
    """ 添加定时任务的校验 """
    project_id: int = Field(..., title="服务id")
    suite_ids: Optional[list] = Field(title="用例集id")
    case_ids: Optional[list] = Field(title="用例id")
    env_list: list = Field(..., title="运行环境")
    name: str = Field(..., title="任务名")
    is_send: SendReportTypeEnum = Field(
        SendReportTypeEnum.ON_FAIL, title="是否发送测试报告", description="not_send/always/on_fail")
    receive_type: ReceiveTypeEnum = Field(
        ReceiveTypeEnum.DING_DING, title="接收测试报告类型", description="ding_ding、we_chat、email")
    webhook_list: list = Field(title="接收消息机器人地址")
    email_server: Optional[str] = Field(title="发件邮箱服务器")
    email_to: list = Field(title="收件人邮箱")
    email_from: Optional[str] = Field(title="发件人邮箱")
    email_pwd: Optional[str] = Field(title="发件人邮箱密码")
    cron: str = Field(..., title="cron表达式")
    conf: Optional[dict] = Field({}, title="运行配置", description="webUi存浏览器，appUi存运行服务器、手机、是否重置APP")
    is_async: int = Field(default=0, title="任务的运行机制", description="0：串行，1：并行，默认0")
    call_back: Optional[Union[list, dict]] = Field(title="回调给流水线")

    def validate_is_send(self):
        """ 发送报告类型 """
        if self.is_send in [SendReportTypeEnum.ALWAYS, SendReportTypeEnum.ON_FAIL]:
            if self.receive_type in (ReceiveTypeEnum.DING_DING, ReceiveTypeEnum.WE_CHAT):
                self.validate_is_true('选择了要通过机器人发送报告，则webhook地址必填', self.webhook_list)
            elif self.receive_type == ReceiveTypeEnum.EMAIL:
                self.validate_email(self.email_server, self.email_from, self.email_pwd, self.email_to)

    def validate_cron(self):
        """ 校验cron格式 """
        try:
            if len(self.cron.strip().split(" ")) == 6:
                CronTab(self.cron + " *")
        except Exception as error:
            raise ValueError(f"时间配置【{self.cron}】错误，需为cron格式, 请检查")
        if self.cron.startswith("*"):  # 每秒钟
            raise ValueError(f"设置的执行频率过高，请重新设置")

    def validate_attrib(self):
        self.validate_is_true(self.name, "任务名不可为空")

    async def validate_request(self, *args, **kwargs):
        self.validate_attrib()
        self.validate_is_send()
        self.validate_cron()
        await self.validate_data_is_not_exist(
            f"当前服务中，任务名【{self.name}】已存在", Task, project_id=self.project_id, name=self.name)


class EditTaskForm(AddTaskForm, GetTaskForm):
    """ 编辑任务 """

    async def validate_request(self, *args, **kwargs):
        self.validate_attrib()
        task = await self.validate_task_is_exist()
        self.validate_is_true(f"任务【{task.name}】的状态不为禁用中，请先禁用再修改", task.is_disable())
        self.validate_is_send()
        self.validate_cron()
        await self.validate_data_is_not_repeat(
            f"当前服务中，任务名【{self.name}】已存在", Task, self.id, project_id=self.project_id, name=self.name)
        return task
