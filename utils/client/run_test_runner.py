import types
import importlib
from threading import Thread

from app.api_test.model_factory import ApiProject, ApiProjectEnv, ApiCaseSuite, ApiCase, ApiStep, ApiMsg, ApiReport
from app.enums import TriggerTypeEnum
from app.ui_test.model_factory import WebUiProject, WebUiProjectEnv, WebUiElement, WebUiCaseSuite, WebUiCase, WebUiStep, \
    WebUiReport
from app.app_test.model_factory import AppUiProject, AppUiProjectEnv, AppUiElement, AppUiCaseSuite, AppUiCase, \
    AppUiStep, AppUiReport
from app.config.model_factory import RunEnv

from app.assist.model_factory import Script
from app.config.model_factory import Config
from utils.client.test_runner.api import TestRunner
from utils.client.test_runner.utils import build_url
# from utils.log import logger
from loguru import logger
from utils.parse.parse import encode_object
from utils.client.parse_model import ProjectModel, ApiModel, CaseModel, ElementModel
from utils.message.send_report import send_report, call_back_for_pipeline
from utils.client.test_runner import validate_func


class RunTestRunner:

    def __init__(self, project_id=None, name=None, report=None, env_code=None, env_name=None,
                 trigger_type=TriggerTypeEnum.PAGE, is_rollback=False, run_type="api", task_dict={}, extend={}):
        self.env_code = env_code  # 运行环境id
        self.env_name = env_name  # 运行环境名，用于发送即时通讯
        self.extend = extend
        self.project_id = project_id
        self.report = report
        self.run_name = name
        self.is_rollback = is_rollback
        self.trigger_type = trigger_type
        self.run_type = run_type
        self.task_dict = task_dict
        self.api_model = ApiMsg
        self.element_model = None
        match self.run_type:
            case "api":  # 接口自动化
                self.project_model = ApiProject
                self.project_env_model = ApiProjectEnv
                self.suite_model = ApiCaseSuite
                self.case_model = ApiCase
                self.step_model = ApiStep
                self.report_model = ApiReport
            case "webUi":  # web-ui自动化
                self.project_model = WebUiProject
                self.project_env_model = WebUiProjectEnv
                self.element_model = WebUiElement
                self.suite_model = WebUiCaseSuite
                self.case_model = WebUiCase
                self.step_model = WebUiStep
                self.report_model = WebUiReport
            case _:  # app-ui自动化
                self.project_model = AppUiProject
                self.project_env_model = AppUiProjectEnv
                self.element_model = AppUiElement
                self.suite_model = AppUiCaseSuite
                self.case_model = AppUiCase
                self.step_model = AppUiStep
                self.report_model = AppUiReport

        self.parsed_project_dict = {}
        self.parsed_case_dict = {}
        self.parsed_api_dict = {}
        self.parsed_element_dict = {}

        self.count_step = 0
        self.api_set = set()
        self.element_set = set()
        self.run_env = None

        # testRunner需要的数据格式
        self.DataTemplate = {
            "is_async": 0,
            "project": self.run_name,
            "run_type": self.run_type,
            "report": self.report,
            "project_mapping": {
                "functions": {},
                "variables": {}
            },
            "testsuites": [],  # 用例集
            "case_list": [],  # 用例
            "apis": [],  # 接口
        }

    async def get_report_addr(self):
        """ 获取报告前端地址 """
        report_host = await Config.get_report_host()
        if self.run_type == "api":  # 接口自动化
            report_addr = await Config.get_api_report_addr()
            return f'{report_host}{report_addr}'
        elif self.run_type == "webUi":  # web-ui自动化
            report_addr = await Config.get_web_ui_report_addr()
            return f'{report_host}{report_addr}'
        else:  # app-ui自动化
            report_addr = await Config.get_app_ui_report_addr()
            return f'{report_host}{report_addr}'

    async def get_format_project(self, project_id):
        """ 从已解析的服务字典中取指定id的服务，如果没有，则取出来解析后放进去 """
        if not self.run_env:
            self.run_env = await RunEnv.filter(code=self.env_code).first()

        if project_id not in self.parsed_project_dict:
            project = await self.project_model.filter(id=project_id).first()
            await self.parse_functions(project.script_list)

            project_env = await self.project_env_model.filter(env_id=self.run_env.id, project_id=project.id).first()

            data = dict(project_env) | dict(project) | dict(self.run_env)
            self.parsed_project_dict.update({project_id: ProjectModel(**data)})
        return self.parsed_project_dict[project_id]

    async def get_format_case(self, case_id):
        """ 从已解析的用例字典中取指定id的用例，如果没有，则取出来解析后放进去 """
        if case_id not in self.parsed_case_dict:
            case = await self.case_model.filter(id=case_id).first()
            if not case:
                return  # 可能存在任务选择了用例，在那边直接把这条用例删掉了的情况
            await self.parse_functions(case.script_list)
            self.parsed_case_dict.update({case_id: CaseModel(**dict(case))})
        return self.parsed_case_dict[case_id]

    async def get_format_element(self, element_id):
        """ 从已解析的元素字典中取指定id的元素，如果没有，则取出来解析后放进去 """
        if element_id not in self.parsed_element_dict:
            element = await self.element_model.filter(id=element_id).first()
            self.parsed_element_dict.update({element_id: ElementModel(**dict(element))})
        return self.parsed_element_dict[element_id]

    async def get_format_api(self, project, api):
        """ 从已解析的接口字典中取指定id的接口，如果没有，则取出来解析后放进去 """
        if api.id not in self.parsed_api_dict:
            if api.project_id not in self.parsed_project_dict:
                project = await self.project_model.filter(id=api.project_id).first()
                await self.parse_functions(project.script_list)
            self.parsed_api_dict.update({api.id: self.parse_api(project, ApiModel(**dict(api)))})
        return self.parsed_api_dict[api.id]

    async def parse_functions(self, script_id_list):
        """ 获取指定脚本中的自定义函数 """
        script_list = await Script.filter(id__in=script_id_list).all()
        for script in script_list:
            script_data = importlib.reload(importlib.import_module(f'script_list.{self.env_code}_{script.name}'))
            self.DataTemplate["project_mapping"]["functions"].update({
                name: item for name, item in vars(script_data).items() if isinstance(item, types.FunctionType)
            })

    def parse_case_is_skip(self, skip_if_list, server_id=None, phone_id=None):
        """ 判断是否跳过用例，暂时只支持对运行环境的判断 """
        for skip_if in skip_if_list:
            skip_type = skip_if["skip_type"]
            if skip_if["data_source"] == "run_env":
                skip_if["check_value"] = self.env_code
            elif skip_if["data_source"] == "run_server":
                skip_if["check_value"] = server_id
            elif skip_if["data_source"] == "run_device":
                skip_if["check_value"] = phone_id
            try:
                comparator = getattr(validate_func, skip_if["comparator"])  # 借用断言来判断条件是否为真
                skip_if_result = comparator(skip_if["check_value"], skip_if["expect"])  # 通过没有返回值
            except Exception as error:
                skip_if_result = error
            if (skip_type == "and" and skip_if_result is None) or (skip_type == "or" and skip_if_result is None):
                return True

    def parse_ui_test_step(self, project, element, step):
        """ 解析 UI自动化测试步骤
        project: 当前步骤对应元素所在的项目(解析后的)
        element: 解析后的element
        step: 原始step
        返回解析后的步骤 {}
        """
        return {
            "name": step.name,
            "setup_hooks": step.up_func,
            "teardown_hooks": step.down_func,
            "skip": not step.status,  # 无条件跳过当前测试
            "skipIf": step.skip_if,  # 如果条件为真，则跳过当前测试
            # "skipUnless": "",  # 除非条件为真，否则跳过当前测试
            "times": step.run_times,  # 运行次数
            "extract": step.extracts,  # 要提取的信息
            "validate": step.validates,  # 断言信息
            "test_action": {
                "execute_name": step.execute_name,
                "action": step.execute_type,
                "by_type": element.by,
                # 如果是打开页面，则设置为项目域名+页面地址
                "element": build_url(project.host, element.element) if element.by == "url" else element.element,
                "text": step.send_keys,
                "wait_time_out": float(step.wait_time_out or element.wait_time_out)
            }
        }

    async def save_report_and_send_message(self, result):
        """ 写入测试报告到数据库, 并把数据写入到文本中 """
        logger.info(f'开始保存测试报告')
        await self.report.save_report_start()
        await self.report.update_report_result(result["result"], summary=result)
        await self.report.save_report_finish()
        logger.info(f'测试报告保存完成')

        # 有可能是多环境一次性批量运行，根据batch_id查是否全部运行完毕
        if await self.report_model.select_is_all_done_by_batch_id(self.report.batch_id):
            not_passed_report = await self.report_model.filter(batch_id=self.report.batch_id, is_passed=0).first()
            if not_passed_report:
                await self.send_report_if_task(not_passed_report.id, not_passed_report.summary)  # 发送报告
            await self.send_report_if_task(self.report.id, result)  # 发送报告

    async def run_case(self):
        """ 调 testRunner().run() 执行测试 """
        logger.info(f'执行测试的数据：\n{self.DataTemplate}')

        if self.DataTemplate.get("is_async", 0):
            # 并行执行, 遍历case，以case为维度多线程执行，测试报告按顺序排列
            run_case_dict = {}
            await self.report.run_case_start()
            for index, case in enumerate(self.DataTemplate["case_list"]):
                run_case_dict[index] = False  # 用例运行标识，索引：是否运行完成
                temp_case = self.DataTemplate
                temp_case["case_list"] = [case]
                self._async_run_case(temp_case, run_case_dict, index)
        else:  # 串行执行
            await self.sync_run_case()

    async def _run_case(self, case, run_case_dict, index):
        runner = TestRunner()
        await runner.run(case)
        self.update_run_case_status(run_case_dict, index, runner.summary)

    def _async_run_case(self, case, run_case_dict, index):
        """ 多线程运行用例 """
        Thread(target=self._run_case, args=[case, run_case_dict, index]).start()

    async def sync_run_case(self):
        """ 单线程运行用例 """
        await self.report.run_case_start()
        runner = TestRunner()
        await runner.run(self.DataTemplate)
        await self.report.run_case_finish()
        logger.info(f'测试执行完成，开始保存测试报告和发送报告')
        summary = runner.summary
        summary["stat"]["count"]["step"] = self.count_step
        summary["stat"]["count"]["api"] = len(self.api_set)
        summary["stat"]["count"]["element"] = len(self.element_set)
        await self.save_report_and_send_message(summary)

    def update_run_case_status(self, run_dict, run_index, summary):
        """ 每条用例执行完了都更新对应的运行状态，如果更新后的结果是用例全都运行了，则生成测试报告"""
        run_dict[run_index] = summary
        if all(run_dict.values()):  # 全都执行完毕
            self.report.run_case_finish()
            all_summary = run_dict[0]
            all_summary["stat"]["count"]["step"] = self.count_step
            all_summary["stat"]["count"]["api"] = len(self.api_set)
            all_summary["stat"]["count"]["element"] = len(self.element_set)
            for index, res in enumerate(run_dict.values()):
                if index != 0:
                    self.build_summary(all_summary, res, ["case_list", "step_list"])  # 合并用例统计, 步骤统计
                    # all_summary["details"].extend(res["details"])  # 合并测试用例数据
                    all_summary["success"] = all([all_summary["success"], res["success"]])  # 测试报告状态
                    all_summary["time"]["case_duration"] = summary["time"]["case_duration"]  # 总共耗时取运行最长的
                    all_summary["time"]["step_duration"] = summary["time"]["step_duration"]  # 总共耗时取运行最长的

            self.save_report_and_send_message(summary)

    async def send_report_if_task(self, report_id, res):
        """ 发送测试报告 """
        if self.task_dict:

            # 如果是流水线触发的，则回调给流水线
            if self.trigger_type == TriggerTypeEnum.PIPELINE:
                logger.info(f'开始回调流水线')
                await call_back_for_pipeline(
                    self.task_dict["id"],
                    self.task_dict["call_back"] or [],
                    self.extend,
                    res["result"]
                )

            # 发送测试报告
            logger.info(f'开始发送测试报告')
            front_report_addr = await self.get_report_addr()
            send_report(content=res, **self.task_dict, report_id=report_id, report_addr=front_report_addr)

    @staticmethod
    def parse_api(project, api):
        """ 把解析后的接口对象 解析为testRunner的数据结构 """
        return {
            "id": api.id,
            "name": api.name,  # 接口名
            "setup_hooks": api.up_func,
            "teardown_hooks": api.down_func,
            "skip": "",  # 无条件跳过当前测试
            "skipIf": "",  # 如果条件为真，则跳过当前测试
            "skipUnless": "",  # 除非条件为真，否则跳过当前测试
            "times": 1,  # 运行次数
            "extract": api.extracts,  # 接口要提取的信息
            "validate": api.validates,  # 接口断言信息
            "base_url": project.host,
            "body_type": api.body_type,
            "variables": [],
            "request": {
                "method": api.method,
                "url": api.addr,
                "timeout": api.time_out,
                "headers": api.headers,  # 接口头部信息
                "params": api.params,  # 接口查询字符串参数
                "json": api.data_json,
                "data": api.data_form,
                "files": api.data_file
            }
        }

    @staticmethod
    def build_summary(source1, source2, fields):
        """ 合并测试报告统计 """
        for field in fields:
            for key in source1["stat"][field]:
                if key != "project":
                    source1["stat"][field][key] += source2["stat"][field][key]
