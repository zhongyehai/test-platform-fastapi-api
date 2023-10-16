from typing import Optional
from pydantic import Field

from app.api_test.model_factory import ApiProject
from app.baseForm import BaseForm, PaginationForm


class FindSwaggerPullListForm(PaginationForm):
    """ 查找swagger拉取记录列表form """
    project_id: int = Field(..., title='服务id')

    def get_query_filter(self, *args, **kwargs):
        """ 查询条件 """

        return {"project_id": self.project_id}


class SwaggerPullForm(BaseForm):
    """ 查找swagger拉取记录列表form """
    project_id: int = Field(..., title='服务id')
    options: list = Field(..., title='拉取项')

    async def validate_request(self, *args, **kwargs):
        return await self.validate_data_is_exist("服务不存在", ApiProject, id=self.project_id)
