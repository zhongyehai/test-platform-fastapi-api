from fastapi import Request

from app.models.autotest.model_factory import ApiProject as Project, ApiModule as Module, ApiMsg as Api, \
    ApiCase as Case, ApiStep as Step, ApiTask as Task, ApiReport as Report
from utils.util.time_util import get_now, time_calculate, get_week_start_and_end
from app.schemas.enums import DataStatusEnum


async def get_data_by_time(model):
    """ 获取时间维度的统计 """
    last_day_add = await model.filter(create_time__range=[time_calculate(-1), time_calculate(0)]).all().count()
    to_day_add = await model.filter(create_time__range=[time_calculate(0), get_now()]).all().count()

    last_start_time, last_end_time = get_week_start_and_end(1)
    last_week_add = await model.filter(create_time__range=[last_start_time, last_end_time]).all().count()

    current_start_time, current_end_time = get_week_start_and_end(0)
    current_week_add = await model.filter(create_time__range=[current_start_time, current_end_time]).all().count()

    last_month_add = await model.filter(create_time__range=[time_calculate(-30), get_now()]).all().count()

    return {
        "last_day_add": last_day_add,
        "to_day_add": to_day_add,
        "last_week_add": last_week_add,
        "current_week_add": current_week_add,
        "last_month_add": last_month_add,
    }


async def get_api_test_title(request: Request):
    return request.app.get_success([
        {"name": "report", "title": "测试报告数", "total": await Report.filter().all().count()},
        {"name": "api", "title": "接口数", "total": await Api.filter().all().count()},
        {"name": "case", "title": "用例数", "total": await Case.filter().all().count()},
        {"name": "step", "title": "测试步骤数", "total": await Step.filter().all().count()}
        # "project": {"title": "服务数", "total": await Project.filter().all().count()},
        # "module": {"title": "模块数", "total": await Module.filter().all().count()},
        # "api": {"title": "接口数", "total": await Api.filter().all().count()},
        # "hit": {"title": "记录问题数", "total": await Hits.filter().all().count()},
        # "case": {"title": "用例数", "total": await Case.filter().all().count()},
        # "step": {"title": "测试步骤数", "total": await Step.filter().all().count()},
        # "task": {"title": "定时任务数", "total": await Task.filter().all().count()},
        # "report": {"title": "测试报告数", "total": await Report.filter().all().count()}
    ])


# async def get_api_test_hit(request: Request):
#     hit_type_data = await Hits.execute_sql("""select hit_type, count(*) num from auto_test_hits group by hit_type""")
#     num_list, hit_type_list = [], ["总数"]
#     for item in hit_type_data:  # [{'hit_type': '123', 'num': 1}, {'hit_type': 'sef', 'num': 1}]
#         num_list.append(item["num"])
#         hit_type_list.append(item["hit_type"])
#     num_list.insert(0, sum(num_list))
#
#     time_data = await get_data_by_time(Hits)
#
#     return request.app.success("获取成功", data={
#         "title": "记录问题",
#         "options": [*hit_type_list, "昨日新增", "今日新增", "本周新增", "上周新增", "30日内新增"],
#         "data": [
#             *num_list,
#             time_data["last_day_add"], time_data["to_day_add"],
#             time_data["current_week_add"], time_data["last_week_add"],
#             time_data["last_month_add"]
#         ]
#     })


async def get_api_test_project(request: Request):
    time_data = await get_data_by_time(Project)
    return request.app.success(data={
        "title": "服务",
        "options": ["总数", "昨日新增", "今日新增", "本周新增", "上周新增", "30日内新增"],
        "data": [
            await Project.filter().all().count(),
            time_data["last_day_add"],
            time_data["to_day_add"],
            time_data["current_week_add"],
            time_data["last_week_add"],
            time_data["last_month_add"]
        ],
    })


async def get_api_test_module(request: Request):
    time_data = await get_data_by_time(Module)
    return request.app.success(data={
        "title": "模块",
        "options": ["总数", "昨日新增", "今日新增", "本周新增", "上周新增", "30日内新增"],
        "data": [
            await Module.filter().all().count(),
            time_data["last_day_add"],
            time_data["to_day_add"],
            time_data["current_week_add"],
            time_data["last_week_add"],
            time_data["last_month_add"]],
    })


async def get_api_test_api(request: Request):
    get_method_count = await Api.filter(method="GET").count()
    post_method_count = await Api.filter(method="POST").count()
    put_method_count = await Api.filter(method="PUT").count()
    delete_method_count = await Api.filter(method="DELETE").count()
    other_method_count = await Api.filter(method__not_in=["GET", "POST", "PUT", "DELETE"]).count()
    is_used_count = await Api.filter(quote_count__not=0).count()
    not_used_count = await Api.filter(quote_count=0).count()
    time_data = await get_data_by_time(Api)
    return request.app.success(data={
        "title": "接口",
        "options": [
            "总数",
            "GET请求", "POST请求", "PUT请求", "DELETE请求", "其他请求",
            "已使用数", "未使用数",
            "昨日新增", "今日新增", "本周新增", "上周新增", "30日内新增"
        ],
        "data": [
            get_method_count + post_method_count + put_method_count + delete_method_count + other_method_count,
            get_method_count, post_method_count, put_method_count, delete_method_count, other_method_count,
            is_used_count, not_used_count,
            time_data["last_day_add"],
            time_data["to_day_add"],
            time_data["current_week_add"],
            time_data["last_week_add"],
            time_data["last_month_add"]
        ]
    })


async def get_api_test_case(request: Request):
    not_run_count = await Case.filter(status=0).count()
    is_run_count = await Case.filter(status__not=0).count()
    time_data = await get_data_by_time(Case)
    return request.app.success("获取成功", data={
        "title": "用例",
        "options": [
            "总数", "要执行的用例", "不执行的用例",
            "昨日新增", "今日新增", "本周新增", "上周新增", "30日内新增"
        ],
        "data": [
            not_run_count + is_run_count, is_run_count, not_run_count,
            time_data["last_day_add"],
            time_data["to_day_add"],
            time_data["current_week_add"],
            time_data["last_week_add"],
            time_data["last_month_add"]
        ],
    })


async def get_api_test_step(request: Request):
    not_run_count = await Step.filter(status=DataStatusEnum.DISABLE.value).count()
    is_run_count = await Step.filter(status=DataStatusEnum.ENABLE.value).count()
    time_data = await get_data_by_time(Step)
    return request.app.success("获取成功", data={
        "title": "测试步骤",
        "options": [
            "总数", "要执行的步骤", "不执行的步骤",
            "昨日新增", "今日新增", "本周新增", "上周新增", "30日内新增"
        ],
        "data": [
            not_run_count + is_run_count, is_run_count, not_run_count,
            time_data["last_day_add"],
            time_data["to_day_add"],
            time_data["current_week_add"],
            time_data["last_week_add"],
            time_data["last_month_add"]
        ],
    })


async def get_api_test_task(request: Request):
    enable_task_count = await Task.filter(status=DataStatusEnum.ENABLE.value).count()
    disable_task_count = await Task.filter(status=DataStatusEnum.DISABLE.value).count()
    time_data = await get_data_by_time(Task)
    return request.app.success("获取成功", data={
        "title": "定时任务",
        "options": [
            "总数", "启用", "禁用",
            "昨日新增", "今日新增", "本周新增", "上周新增", "30日内新增"
        ],
        "data": [
            enable_task_count + disable_task_count, enable_task_count, disable_task_count,
            time_data["last_day_add"],
            time_data["to_day_add"],
            time_data["current_week_add"],
            time_data["last_week_add"],
            time_data["last_month_add"]
        ]
    })


async def get_api_test_report(request: Request):
    is_passed_count = await Report.filter(is_passed=1).count()
    not_passed_count = await Report.filter(is_passed__not=1).count()
    api_report_count = await Report.filter(run_type="api").count()
    case_report_count = await Report.filter(run_type="case").count()
    suite_report_count = await Report.filter(run_type="set").count()
    task_report_count = await Report.filter(run_type="task").count()
    time_data = await get_data_by_time(Report)
    return request.app.success("获取成功", data={
        "title": "测试报告",
        "options": [
            "总数", "通过数", "失败数",
            "接口生成", "用例生成", "用例集生成", "定时任务生成",
            "昨日新增", "今日新增", "本周新增", "上周新增", "30日内新增"
        ],
        "data": [
            is_passed_count + not_passed_count,
            is_passed_count, not_passed_count,
            api_report_count, case_report_count, suite_report_count, task_report_count,
            time_data["last_day_add"],
            time_data["to_day_add"],
            time_data["current_week_add"],
            time_data["last_week_add"],
            time_data["last_month_add"]
        ]
    })
