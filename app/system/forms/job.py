from typing import Optional
from pydantic import Field

from ...baseForm import BaseForm, PaginationForm
from ..model_factory import ApschedulerJobs


class GetJobRunLogList(PaginationForm):
    func_name: Optional[str] = Field(..., title="方法名")

    def get_query_filter(self, *args, **kwargs):
        """ 查询条件 """
        filter_dict = {}
        if self.func_name:
            filter_dict["func_name"] = self.func_name

        return filter_dict


class GetJobForm(BaseForm):
    """ 获取job信息 """

    task_code: str = Field(..., title="job code")

    async def validate_job_is_exist(self):
        return await self.validate_data_is_exist("任务不存在", ApschedulerJobs, task_code=self.task_code)

    async def validate_request(self, *args, **kwargs):
        return await self.validate_job_is_exist()


class AddJobForm(BaseForm):
    """ 新增job信息 """

    func: str = Field(..., title="job方法")
