import asyncio
import copy
import json
from fastapi import Request

from ..forms.job import GetJobRunLogList, GetJobForm, AddJobForm
from ..routers import system_router
from ..model_factory import ApschedulerJobs, JobRunLog
from ...config.model_factory import BusinessLine
from ...api_test.model_factory import ApiProject as Project, ApiReport, ApiReportCase, ApiReportStep
from ...enums import ReceiveTypeEnum
from ...ui_test.model_factory import WebUiReport, WebUiReportCase, WebUiReportStep
from ...app_test.model_factory import AppUiReport, AppUiReportCase, AppUiReportStep
from utils.message.send_report import send_business_stage_count
from utils.util import request as async_request
from config import job_server_host


class JobFuncs:
    """ 定时任务，方法以cron_开头，参数放在文档注释里面 """

    @classmethod
    async def cron_clear_report(cls):
        """
        {
            "name": "清理测试报告",
            "id": "cron_clear_report",
            "cron": "0 0 2 * * ?",
            "skip_holiday": true
        }
        """

        # 清理已删除的测试报告主数据下的报告数据
        report_type_model_list = [
            [ApiReport, ApiReportCase, ApiReportStep],
            [WebUiReport, WebUiReportCase, WebUiReportStep],
            [AppUiReport, AppUiReportCase, AppUiReportStep]
        ]
        for report_model_list in report_type_model_list:
            report_model, report_case_model, report_step_model = report_model_list
            await report_model.clear_case_and_step(report_case_model, report_step_model)

    @classmethod
    async def cron_count_of_week(cls):
        """
        {
            "name": "周统计任务",
            "id": "cron_count_of_week",
            "cron": "0 0 18 ? * FRI",
            "skip_holiday": false
        }
        """

        await cls.run_task_report_count("cron_count_of_week", "week")

    @classmethod
    async def cron_count_of_month(cls):
        """
        {
            "name": "月统计任务",
            "id": "cron_count_of_month",
            "cron": "0 1 18 last * *",
            "skip_holiday": false
        }
        """
        await cls.run_task_report_count("cron_count_of_month", "month")

    @staticmethod
    async def run_task_report_count(run_func, count_time="month"):
        """ 自动化测试记录阶段统计 """

        if count_time == "week":
            count_day = 'YEARWEEK(DATE_FORMAT(create_time,"%Y-%m-%d"))=YEARWEEK(NOW())'
        elif count_time == "month":
            count_day = 'DATE_FORMAT(create_time, "%Y%m") = DATE_FORMAT(CURDATE(), "%Y%m")'

        business_list = await BusinessLine.filter(receive_type__not=ReceiveTypeEnum.NOT_RECEIVE).all()

        for business in business_list:
            run_log = await JobRunLog.create(business_id=business.id, func_name=run_func)
            business_template = {
                "countTime": count_time,
                "total": 0,
                "pass": 0,
                "fail": 0,
                "passRate": 0,
                "record": [],
                "hitRecord": {}
            }

            project_list = await Project.filter(business_id=business.id).all()
            for project in project_list:

                project_template = copy.deepcopy(business_template)
                project_template.pop("countTime")

                data_report = await ApiReport.execute_sql(f"""SELECT
                       project_id,
                       sum( CASE is_passed WHEN 1 THEN 1 ELSE 0 END ) AS pass,
                       sum( CASE is_passed WHEN 0 THEN 1 ELSE 0 END ) AS fail 
                   FROM
                       api_test_report WHERE `trigger_type` in ("cron", "pipeline") 
                       AND project_id in ({project.id})
                       AND `process` = '3' 
                       AND `status` = '2' 
                       AND {count_day}""")

                data_hit = await ApiReport.execute_sql(
                    f"""SELECT project_id,hit_type,count(hit_type)  FROM auto_test_hits 
                           WHERE project_id in ({project.id}) AND {count_day} GROUP BY hit_type """)
                print(data_report)
                pass_count = int(data_report[0]["pass"]) if data_report[0]["pass"] else 0
                fail_count = int(data_report[0]["fail"]) if data_report[0]["fail"] else 0
                total = pass_count + fail_count
                if total != 0:
                    project_template["name"] = project.name
                    project_template["total"] = total
                    project_template["pass"] = pass_count
                    project_template["fail"] = fail_count
                    project_template["passRate"] = round(pass_count / total, 3) if total > 0 else 0
                    project_template["hitRecord"] = {hit[1]: hit[2] for hit in data_hit}
                    project_template["record"] = []
                    business_template["record"].append(project_template)

            # 聚合业务线的数据
            business_template["webhookList"] = business.webhook_list
            business_template["receiveType"] = business.receive_type
            for project_count in business_template["record"]:
                business_template["total"] += project_count["total"]
                business_template["pass"] += project_count["pass"]
                business_template["fail"] += project_count["fail"]
                business_template["passRate"] += project_count["passRate"]
                for key, value in project_count["hitRecord"].items():
                    hit_record_key = business_template["hitRecord"].get(key)
                    business_template["hitRecord"][key] = hit_record_key + value if hit_record_key else value

            if business_template["total"] > 0:
                business_template["passRate"] = business_template["passRate"] / len(business_template["record"])
                send_business_stage_count(business_template)
            await run_log.run_success(business_template)


@system_router.admin_post("/job/func/list", summary="获取定时任务方法列表")
async def get_job_func_list(request: Request):
    data_list = []
    for func_name in dir(JobFuncs):
        if func_name.startswith("cron_"):
            attr_doc = json.loads(getattr(JobFuncs, func_name).__doc__)
            func = {"name": attr_doc["name"], "func_name": attr_doc["id"], "cron": attr_doc["cron"]}
            job = await ApschedulerJobs.filter(task_code=f'cron_{attr_doc["id"]}').first()
            if job:
                func["task_code"] = job.task_code
                func["next_run_time"] = job.next_run_time
            data_list.append(func)
    return request.app.get_success(data_list)


# @system_router.admin_post("/job/list", summary="获取定时任务列表")
# async def get_user_list(request: Request):
#     job_list = await ApschedulerJobs.filter().all().values_list("job_code", "next_run_time")
#     return request.app.get_success(
#         data=[{"id": job.id, "next_run_time": job.next_run_time} for job in job_list])


@system_router.login_post("/job/run", summary="执行任务")
async def run_job(form: AddJobForm, request: Request):
    # Thread(target=getattr(JobFuncs, func)).start()  # 异步执行，释放资源
    asyncio.create_task(getattr(JobFuncs, form.func)())
    return request.app.success("触发成功")


@system_router.login_post("/job/log", summary="执行任务记录")
async def get_job_log_list(form: GetJobRunLogList, request: Request):
    query_data = await form.make_pagination(JobRunLog)
    return request.app.get_success(data=query_data)


@system_router.login_post("/job/detail", summary="获取定时任务")
async def get_job_detail(form: GetJobForm, request: Request):
    job = await form.validate_request()
    return request.app.get_success(data=job)


@system_router.admin_post("/job", summary="新增定时任务")
async def add_job(form: AddJobForm, request: Request):
    task_conf = getattr(JobFuncs, form.func).__doc__
    try:
        res = await async_request.post(
            url=job_server_host,
            headers={"X-Token": request.headers.get("X-Token")},
            json={
                "task": form.loads(task_conf),
                "task_type": "cron"
            }
        )
        request.app.logger.info(f'添加任务【{form.func}】响应: \n{res.json()}')
        return request.app.success('操作成功')
    except:
        return request.app.error('操作失败')


@system_router.admin_delete("/job", summary="删除定时任务")
async def delete_job(form: GetJobForm, request: Request):
    try:
        res = await async_request.delete(
            url=job_server_host,
            headers={"X-Token": request.headers.get("X-Token")},
            json={
                "task_code": form.task_code
            })
        request.app.logger.info(f'删除任务【{form.task_code}】响应: \n{res.json()}')
        return request.app.success('操作成功')
    except:
        return request.app.error('操作失败')
