from typing import Optional
from pydantic import Field
from fastapi import Request

# from app.assist.models.hits import Hits
from ...baseForm import BaseForm, PaginationForm
from ..model_factory import WebUiReport as Report, WebUiReportStep as ReportStep, WebUiReportCase as ReportCase


class FindReportForm(PaginationForm):
    """ 查询报告 """
    project_id: int = Field(..., title="服务id")
    report_name: Optional[str] = Field(title="报告名")
    create_user: Optional[int] = Field(title="创建人")
    trigger_type: Optional[str] = Field(title="触发类型")
    run_type: Optional[str] = Field(title="执行类型")
    is_passed: Optional[int] = Field(title="是否通过")
    env_list: Optional[list] = Field(title="运行环境")

    def get_query_filter(self, *args, **kwargs):
        """ 查询条件 """
        filter_dict = {"project_id": self.project_id}
        if self.report_name:
            filter_dict["report_name__icontains"] = self.report_name
        if self.create_user:
            filter_dict["create_user"] = self.create_user
        if self.trigger_type:
            filter_dict["trigger_type"] = self.trigger_type
        if self.run_type:
            filter_dict["run_type"] = self.run_type
        if self.is_passed:
            filter_dict["is_passed"] = self.is_passed
        if self.env_list:
            filter_dict["env__in"] = self.env_list
        return filter_dict


class GetReportForm(BaseForm):
    """ 获取报告 """
    id: int = Field(..., title="报告id")

    async def validate_request(self, *args, **kwargs):
        return await self.validate_data_is_exist("任务不存在", Report, id=self.id)


class DeleteReportForm(BaseForm):
    """ 删除报告 """
    id_list: list = Field(..., title="报告id list")

    async def validate_request(self, request: Request, *args, **kwargs):

        report_list = await Report.filter(id__in=self.id_list).all()
        report_id_list = []
        for report in report_list:
            # 出于周统计、月统计的数据准确性考虑，触发方式为 pipeline 和 cron，只有管理员权限能删
            if report.trigger_type in ['pipeline', 'cron'] and self.is_not_admin(
                    request.state.user.api_permissions):
                continue

            # 没有被登记失败记录的报告可以删
            # if Hits.get_first(report_id=report.id) is None:
            #     report_id_list.append(report.id)
            report_id_list.append(report.id)

        return report_id_list


class GetReportCaseListForm(PaginationForm):
    """ 获取报告用例列表 """
    report_id: int = Field(..., title="报告id")
    get_summary: Optional[bool] = Field(title="是否获取详情")


class GetReportCaseForm(BaseForm):
    """ 获取报告步骤数据 """
    id: int = Field(..., title="报告用例id")

    async def validate_request(self, *args, **kwargs):
        return await self.validate_data_is_exist("数据不存在", ReportCase, id=self.id)


class GetReportStepListForm(PaginationForm):
    """ 获取报告步骤列表 """
    report_case_id: int = Field(..., title="报告用例id")
    get_summary: Optional[bool] = Field(title="是否获取详情")


class GetReportStepForm(BaseForm):
    """ 获取报告步骤数据 """
    id: int = Field(..., title="报告步骤id")

    async def validate_request(self, *args, **kwargs):
        return await self.validate_data_is_exist("数据不存在", ReportStep, id=self.id)


class GetReportStepImgForm(BaseForm):
    """ 获取报告步骤截图 """
    report_id: int = Field(..., title="测试报告id")
    report_step_id: int = Field(..., title="报告步骤id")
    img_type: str = Field(..., title="截图类型，before_page, after_page")


class GetReportShowIdForm(BaseForm):
    """ 获取报告状态 """

    batch_id: str = Field(..., title="执行批次id")


class GetReportStatusForm(GetReportShowIdForm):
    """ 获取报告状态 """

    process: int = Field(1, title="当前进度")
    status: int = Field(1, title="当前进度下的状态")
