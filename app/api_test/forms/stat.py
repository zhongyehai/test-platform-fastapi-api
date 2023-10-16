from typing import Optional
from pydantic import Field

from ...baseForm import BaseForm
from ..model_factory import ApiProject as Project
from ...enums import TriggerTypeEnum


class UseCountForm(BaseForm):
    time_slot: int = Field(..., title="时间切片")


class AnalyseForm(BaseForm):
    business_id: int = Field(..., title="业务线id")
    trigger_type: Optional[TriggerTypeEnum] = Field(title="触发类型")
    start_time: Optional[str] = Field(title="开始时间")
    end_time: Optional[str] = Field(title="结束时间")

    async def get_filters(self):
        query_set = await Project.filter(business_id=self.business_id).values("id")  # [{"id": 1}]
        filter_dict = {"project_id__in": [project_query["id"] for project_query in query_set]}

        if self.trigger_type:
            filter_dict["trigger_type"] = self.trigger_type
        if self.start_time:
            filter_dict["create_time__range"] = [self.start_time, self.end_time]
        return filter_dict
