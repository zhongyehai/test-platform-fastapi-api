from typing import List
from fastapi import Request, BackgroundTasks

from ..routers import api_test
from ..model_factory import ApiReport as Report, ApiReportCase as ReportCase, ApiReportStep as ReportStep, \
    ApiReportPydantic as ReportPydantic, ApiReportCasePydantic as ReportCasePydantic, \
    ApiReportStepPydantic as ReportStepPydantic
from ..forms.report import GetReportForm, FindReportForm, DeleteReportForm, GetReportCaseForm, \
    GetReportCaseListForm, GetReportStepForm, GetReportStepListForm, GetReportStatusForm, GetReportShowIdForm


@api_test.login_post("/report/list", response_model=List[ReportPydantic], summary="获取测试报告列表")
async def api_get_report_list(form: FindReportForm, request: Request):
    query_data = await form.make_pagination(Report)
    return request.app.get_success(data=query_data)


@api_test.post("/report/case/list", response_model=List[ReportCasePydantic], summary="获取报告的用例列表")
async def api_get_report_case_list(form: GetReportCaseListForm, request: Request):
    case_list = await ReportCase.get_resport_case_list(form.report_id, form.get_summary)
    return request.app.get_success(case_list)


@api_test.post("/report/case", summary="获取报告的用例数据")
async def api_get_report_case(form: GetReportCaseForm, request: Request):
    report_case = await form.validate_request()
    return request.app.get_success(report_case)


@api_test.post("/report/step/list", response_model=List[ReportStepPydantic], summary="获取报告的步骤列表")
async def api_get_report_step_list(form: GetReportStepListForm, request: Request):
    step_list = await ReportStep.get_resport_step_list(form.report_case_id, form.get_summary)
    return request.app.get_success(step_list)


@api_test.post("/report/step", summary="获取报告的步骤数据")
async def api_get_report_step(form: GetReportStepForm, request: Request):
    report_step = await form.validate_request()
    return request.app.get_success(report_step)


@api_test.login_post("/report/status", summary="根据运行id获取当次报告是否全部生成")
async def api_get_report_status(form: GetReportStatusForm, request: Request):
    data = await Report.select_is_all_status_by_batch_id(form.batch_id, [form.process, form.status])
    return request.app.get_success(data)


@api_test.login_post("/report/show/id", summary="根据运行id获取当次要打开的报告")
async def api_get_report_show_id(form: GetReportShowIdForm, request: Request):
    data = await Report.select_show_report_id(form.batch_id)
    return request.app.get_success(data)


@api_test.login_delete("/report/clear", summary="清除测试报告")
async def api_report_clear(request: Request, background_tasks: BackgroundTasks):
    # 清除报告数据比较耗时，用后台任务机制
    background_tasks.add_task(Report.clear_case_and_step, ReportCase, ReportStep)
    return request.app.success("触发清除成功")


@api_test.post("/report/detail", summary="获取测试报告")
async def api_get_report_detail(form: GetReportForm, request: Request):
    report = await form.validate_request()
    return request.app.get_success(report)


@api_test.login_delete("/report", summary="删除测试报告主数据")
async def api_delete_report(form: DeleteReportForm, request: Request):
    id_list = await form.validate_request(request.state.user)
    await Report.filter(id__in=id_list).delete()
    return request.app.delete_success()
