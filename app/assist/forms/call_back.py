from typing import Optional
from pydantic import Field

from app.baseForm import PaginationForm


class FindCallBackForm(PaginationForm):
    """ 查找回调记录列表form """
    url: Optional[str] = Field(title='接口地址')

    def get_query_filter(self, *args, **kwargs):
        """ 查询条件 """
        filter_dict = {}
        if self.url:
            filter_dict["url__icontains"] = self.url
        return filter_dict
