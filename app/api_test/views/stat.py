from typing import List
from fastapi import Request

from ..routers import api_test
from ..model_factory import ApiReport as Report, ApiReportCase as ReportCase, ApiReportPydantic as ReportPydantic, \
    ApiProject as Project, ApiCaseSuite as Suite, ApiCase as Case
from ...config.model_factory import BusinessLine
from ..forms.stat import UseCountForm, AnalyseForm
from utils.util.time_util import time_calculate, get_now
from ...enums import ApiCaseSuiteTypeEnum
from utils.log import logger


async def get_use_stat(time_slot, project_list: list = []):
    """ 获取时间段的统计 """
    start_time, end_time = time_calculate(time_slot), get_now()
    time_filter = {"create_time__range": [start_time, end_time]}
    project_filter = {"project_id__in": project_list}
    run_type = {"run_type": "task"}
    is_passed = {"is_passed": 1}
    use_count, use_pass_count, use_pass_rate = 0, 0, 0  # 使用次数维度
    patrol_count, patrol_pass_count, patrol_pass_rate = 0, 0, 0  # 巡检维度

    # 使用统计
    use_count_query = Report.filter(**time_filter, **project_filter) if project_list else Report.filter(**time_filter)
    use_count = await use_count_query.count()
    if use_count > 0:
        pass_count_query = Report.filter(
            **time_filter, **is_passed, **project_filter) if project_list else Report.filter(**time_filter, **is_passed)
        use_pass_count = await pass_count_query.count()
        use_pass_rate = round(use_pass_count / use_count, 4)

    # 巡检统计
    patrol_count_query = Report.filter(
        **time_filter, **run_type, **project_filter) if project_list else Report.filter(**time_filter, **run_type)
    patrol_count = await patrol_count_query.count()
    if patrol_count > 0:
        patrol_pass_query = Report.filter(
            **time_filter, **is_passed, **run_type, **project_filter
        ) if project_list else Report.filter(**time_filter, **is_passed, **run_type)
        patrol_pass_count = await patrol_pass_query.count()
        patrol_pass_rate = round(patrol_pass_count / patrol_count, 4)

    # 造数据统计
    if not project_list:
        project_query_set = await Project.filter().values("id")
        project_list = [query_set["id"] for query_set in project_query_set]

    suite_list = [query_set["id"] for query_set in await Suite.filter(
        project_id__in=project_list, suite_type=ApiCaseSuiteTypeEnum.MAKE_DATA).values("id")]
    case_list = [query_set["id"] for query_set in await Case.filter(suite_id__in=suite_list).values("id")]
    make_data_count = await ReportCase.filter(case_id__in=case_list, **time_filter).distinct().values("report_id")

    return {
        "use_count": use_count, "use_pass_count": use_pass_count, "use_pass_rate": use_pass_rate,
        "patrol_count": patrol_count, "patrol_pass_count": patrol_pass_count, "patrol_pass_rate": patrol_pass_rate,
        "make_data_count": len(make_data_count)
    }


@api_test.login_post("/stat/use/card", response_model=List[ReportPydantic], summary="使用统计卡片")
async def api_get_report_list(form: UseCountForm, request: Request):
    use_stat = await get_use_stat(form.time_slot)
    return request.app.get_success(data=use_stat)


@api_test.login_post("/stat/use/chart", response_model=List[ReportPydantic], summary="使用统计图表")
async def api_get_report_list(form: UseCountForm, request: Request):
    options_list = []
    use_count_list, use_pass_count_list, use_pass_rate_list = [], [], []  # 使用维度
    patrol_count_list, patrol_pass_count_list, patrol_pass_rate_list = [], [], []  # 巡检维度
    make_data_count_list = []  # 造数据维度

    business_list = await BusinessLine.filter().values("id", "name")  # [{"id", 1, "name": "公共业务线"}]
    for business_line in business_list:
        options_list.append(business_line["name"])
        project_id_list = await Project.filter(business_id=business_line["id"]).values("id")  # [{"id", 1}]
        business_stat = await get_use_stat(form.time_slot, [query_set["id"] for query_set in project_id_list])

        use_count_list.append(business_stat.get("use_count", 0))
        use_pass_count_list.append(business_stat.get("use_pass_count", 0))
        use_pass_rate_list.append(business_stat.get("use_pass_rate", 0))
        patrol_count_list.append(business_stat.get("patrol_count", 0))
        patrol_pass_count_list.append(business_stat.get("patrol_pass_count", 0))
        patrol_pass_rate_list.append(business_stat.get("patrol_pass_rate", 0))
        make_data_count_list.append(business_stat.get("make_data_count", 0))

    return request.app.get_success({
        "options_list": options_list,
        "use_count_list": use_count_list,
        "use_pass_count_list": use_pass_count_list,
        "use_pass_rate_list": use_pass_rate_list,
        "patrol_count_list": patrol_count_list,
        "patrol_pass_count_list": patrol_pass_count_list,
        "patrol_pass_rate_list": patrol_pass_rate_list,
        "make_data_count_list": make_data_count_list
    })


@api_test.login_post("/stat/analyse", response_model=List[ReportPydantic], summary="获取测试报告列表")
async def api_get_report_list(form: AnalyseForm, request: Request):
    filters = await form.get_filters()

    # 执行次数维度统计
    all_count = await Report.filter(**filters).count()
    pass_count = await Report.filter(**filters, is_passed=1).count()
    fail_count = all_count - pass_count

    # 创建人执行次数统计
    user_count_sql = """
        SELECT user.name AS name, count(user.id) AS value
        FROM system_user user,
             api_test_report report,
             api_test_project project
        WHERE report.project_id = project.id
          AND project.business_id = 1
          AND user.id = report.create_user
    """
    if form.trigger_type:
        user_count_sql += f"""AND report.trigger_type = '{form.trigger_type.value}' \n"""
    if form.start_time:
        user_count_sql += f"""AND report.create_time between '{form.start_time}' and '{form.end_time}' \n"""
    user_count_sql += """GROUP BY report.create_user"""
    logger.info(f'api.report.stat.analyse.user_count_sql: {user_count_sql}')
    user_count_list = await Report.execute_sql(user_count_sql)

    return request.app.get_success({
        "use_count": {
            "stat": {
                "title": "执行次数统计",
                "stat_list": [
                    {"name": "通过数量", "value": pass_count},
                    {"name": "不通过数量", "value": fail_count},
                ]
            },
            "detail": {"all_count": all_count, "pass_count": pass_count, "fail_count": fail_count}
        },
        "create": {
            "stat": {
                "title": "执行人员统计",
                "stat_list": user_count_list
            }
        }
    })
