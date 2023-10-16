from typing import Optional, List
from pydantic import Field

from ...baseForm import BaseForm, PaginationForm
from ..model_factory import BugTrack


class GetBugListForm(PaginationForm):
    business_list: Optional[List[int]] = Field(title="业务线")
    name: Optional[str] = Field(title="bug名字关键字")
    detail: Optional[str] = Field(title="bug详情关键字")
    status: Optional[str] = Field(title="bug状态")
    replay: Optional[str] = Field(title="bug是否复盘")
    conclusion: Optional[str] = Field(title="复盘结论")
    iteration: Optional[str] = Field(title="迭代")

    def get_query_filter(self, *args, **kwargs):
        """ 查询条件 """
        user, filter_dict = kwargs.get("user"), {}

        if self.business_list:
            # business_list = set(self.business_list) & set(user.business_list)  # 取并集
            filter_dict["business_id__in"] = self.business_list
        else:
            if self.is_not_admin(user.api_permissions):  # 非管理员则校验业务线权限
                filter_dict["business_id__in"] = user.business_list
        if self.name:
            filter_dict["name__icontains"] = self.name
        if self.detail:
            filter_dict["detail__icontains"] = self.detail
        if self.status:
            filter_dict["status"] = self.status
        if self.replay:
            filter_dict["replay"] = self.replay
        if self.conclusion:
            filter_dict["conclusion__icontains"] = self.conclusion
        if self.iteration:
            filter_dict["iteration"] = self.iteration
        return filter_dict


class GetBugForm(BaseForm):
    id: int = Field(..., title="bug数据id")

    async def validate_bug_is_exist(self):
        return await self.validate_data_is_exist("bug不存在", BugTrack, id=self.id)

    async def validate_request(self, *args, **kwargs):
        return await self.validate_bug_is_exist()


class DeleteBugForm(GetBugForm):
    """ 删除bug """

    async def validate_request(self, *args, **kwargs):
        return await self.validate_bug_is_exist()


class ChangeBugStatusForm(GetBugForm):
    """ 修改bug状态 """
    status: str = Field(..., title="bug状态")

    async def validate_request(self, *args, **kwargs):
        return await self.validate_bug_is_exist()


class ChangeBugReplayForm(GetBugForm):
    """ 修改bug是否复盘 """
    replay: str = Field(..., title="复盘状态")

    async def validate_request(self, *args, **kwargs):
        return await self.validate_bug_is_exist()


class AddBugForm(BaseForm):
    business_id: int = Field(..., title="业务线")
    iteration: str = Field(..., title="迭代")
    name: str = Field(..., title="bug描述")
    detail: str = Field(..., title="bug详情")
    bug_from: Optional[str] = Field(..., title="来源")
    trigger_time: Optional[str] = Field(..., title="发现时间")
    reason: Optional[str] = Field(..., title="原因")
    solution: Optional[str] = Field(..., title="解决方案")
    manager: Optional[int] = Field(..., title="跟进人")
    replay: int = Field(..., title="是否复盘")
    conclusion: Optional[int] = Field(..., title="复盘结论")

    def validate_replay(self):
        if self.replay:  # 已复盘，则必须有复盘结论
            self.validate_is_true("请输入复盘结论", self.conclusion)

    async def validate_request(self, *args, **kwargs):
        self.validate_replay()


class ChangeBugForm(GetBugForm, AddBugForm):
    """ 修改bug """

    async def validate_request(self, *args, **kwargs):
        self.validate_replay()
        return await self.validate_bug_is_exist()
