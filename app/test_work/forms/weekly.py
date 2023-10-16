from typing import Optional, Union
from pydantic import Field

from ...baseForm import BaseForm, PaginationForm
from ..model_factory import WeeklyModel, WeeklyConfigModel


class GetWeeklyConfigListForm(PaginationForm):
    name: Optional[str] = Field(title="名字")
    parent: Optional[str] = Field(title="父级")

    def get_query_filter(self, *args, **kwargs):
        """ 查询条件 """
        filter_dict = {}
        if self.name:
            filter_dict["name__icontains"] = self.name
        if self.parent:
            filter_dict["parent"] = self.parent

        return filter_dict


class GetWeeklyConfigForm(BaseForm):
    """ 获取产品、项目 """
    id: int = Field(..., title="产品或项目id")

    async def validate_weekly_config_is_exist(self):
        return await self.validate_data_is_exist("产品或项目不存在", WeeklyConfigModel, id=self.id)

    async def validate_request(self, *args, **kwargs):
        return await self.validate_weekly_config_is_exist()


class DeleteWeeklyConfigForm(GetWeeklyConfigForm):
    """ 删除产品、项目 """

    async def validate_request(self, *args, **kwargs):
        weekly_config = await self.validate_weekly_config_is_exist()

        if not weekly_config.parent:  # 产品
            # 判断产品下无项目
            await self.validate_data_is_not_exist("当前产品下还有项目，请先删除项目", WeeklyConfigModel, parent=self.id)
            # 判断产品下无周报
            await self.validate_data_is_not_exist("当前产品下还有周报，请先删除周报", WeeklyModel, product_id=self.id)
        else:  # 项目
            # 判断项目下无周报
            await self.validate_data_is_not_exist("当前项目下还有周报，请先删除周报", WeeklyModel, project_id=self.id)
        return weekly_config


class AddWeeklyConfigForm(BaseForm):
    """ 添加产品、项目 """
    name: int = Field(..., title="名称")
    parent: Optional[int] = Field(title="父级")
    desc: Optional[str] = Field(title="描述")

    async def validate_request(self, *args, **kwargs):

        if self.parent:  # 有父级，为项目
            await self.validate_data_is_not_exist(
                f"当前节点下已存在名为【{self.name}】的项目", WeeklyConfigModel, name=self.name, parent=self.parent)
        else:  # 没有父级，为产品
            await self.validate_data_is_not_exist(
                f"已存在名为【{self.name}】的产品", WeeklyConfigModel, name=self.name, parent=None)


class ChangeWeeklyConfigForm(GetWeeklyConfigForm, AddWeeklyConfigForm):
    """ 修改产品、项目 """

    async def validate_request(self, *args, **kwargs):
        weekly_config = await self.validate_weekly_config_is_exist()
        if self.parent:  # 产品
            await self.validate_data_is_not_repeat(
                f"已存在名为【{self.name}】的产品", WeeklyConfigModel, self.id, name=self.name, parent=None)
        else:  # 项目
            await self.validate_data_is_not_repeat(
                f"当前产品下项目【{self.name}】已存在", WeeklyConfigModel, self.id, name=self.name, parent=self.parent)


class GetWeeklyListForm(PaginationForm):
    product_id: Optional[int] = Field(title="产品id")
    project_id: Optional[int] = Field(title="项目id")
    create_user: Optional[int] = Field(title="创建人")
    version: Optional[str] = Field(title="版本")
    task_item: Optional[str] = Field(title="任务明细")
    start_time: Optional[str] = Field(title="开始时间")
    end_time: Optional[str] = Field(title="结束时间")

    def get_query_filter(self, *args, **kwargs):
        """ 查询条件 """
        filter_dict = {}
        if self.product_id:
            filter_dict["product_id"] = self.product_id
        if self.project_id:
            filter_dict["project_id"] = self.project_id
        if self.version:
            filter_dict["version"] = self.version
        if self.task_item:
            filter_dict["task_item__icontains"] = self.task_item
        if self.start_time:
            filter_dict["start_time__gte"] = self.start_time
        if self.end_time:
            filter_dict["end_time__lte"] = self.end_time
        if self.create_user:
            filter_dict["create_user"] = self.create_user
        return filter_dict


class GetWeeklyForm(BaseForm):
    """ 获取周报 """
    id: int = Field(..., title="周报id")

    async def validate_weekly_is_exist(self):
        return await self.validate_data_is_exist("产品或项目不存在", WeeklyConfigModel, id=self.id)

    async def validate_request(self, *args, **kwargs):
        return await self.validate_weekly_is_exist()


class DeleteWeeklyForm(GetWeeklyForm):
    """ 删除周报 """


class DownloadWeeklyForm(GetWeeklyForm):
    download_type: Optional[Union[str, None]] = Field(title="下载时间段类型")


class AddWeeklyForm(BaseForm):
    """ 添加周报 """
    product_id: Optional[int] = Field(title="产品id")
    project_id: Optional[int] = Field(title="项目id")
    version: str = Field(..., title="版本号")
    task_item: str = Field(..., title="任务明细")
    desc: Optional[str] = Field(title="备注")
    start_time: Optional[str] = Field(title="开始时间")
    end_time: Optional[str] = Field(title="结束时间")

    async def validate_product_id(self, *args, **kwargs):
        # 校验产品id或者项目id必须存在
        if self.product_id:
            await self.validate_data_is_exist("产品不存在", WeeklyConfigModel, id=self.product_id)
        elif self.project_id:
            await self.validate_data_is_exist("项目不存在", WeeklyConfigModel, id=self.project_id)
        else:
            raise ValueError("请选择产品或者项目")

    def validate_task_item(self):
        # 校验任务明细必须有值：[{"item": "xxx", "progress": "50%"}]
        task_item_container = []
        for index, data in enumerate(self.task_item):
            key, value = data.get("key", ""), data.get("value", "")
            if key and value:
                task_item_container.append(index)
            elif key and not value:
                raise ValueError(f"任务明细第【{index + 1}】项，测试进度未填写")
            elif value and not key:
                raise ValueError(f"任务明细第【{index + 1}】项，测试任务未填写")
        if not task_item_container:
            raise ValueError("请完善测试任务明细")

    async def validate_start_time(self, user, *args, **kwargs):
        # 同一个产品，同一个项目，同一个版本号，同一个人，同一周只能有一条数据
        await self.validate_data_is_not_exist(
            "你已经填写过当前时间段在当前项目的周报",
            WeeklyModel, product_id=self.product_id, project_id=self.project_id, version=self.version.strip(),
            start_time=self.start_time, create_user=user.id
        )

    async def validate_request(self, user, *args, **kwargs):
        self.validate_task_item()
        await self.validate_product_id()
        await self.validate_start_time(user)


class ChangeWeeklyForm(GetWeeklyForm, AddWeeklyForm):
    """ 修改周报 """

    async def validate_request(self, user, *args, **kwargs):
        weekly = await self.validate_weekly_is_exist()
        self.validate_task_item()
        await self.validate_product_id()
        # 同一个产品，同一个项目，同一个版本号，同一个人，同一周只能有一条数据
        await self.validate_data_is_not_repeat(
            "你已经填写过当前时间段在当前项目的周报",
            WeeklyModel, weekly.id, product_id=self.product_id, project_id=self.project_id,
            version=self.version.strip(), start_time=self.start_time, create_user=user.id
        )
        return weekly
