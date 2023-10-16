import datetime
import traceback

from loguru import logger
from . import exceptions, parser, runner


class TestRunner:

    def __init__(self):
        self.summary = None

    async def run_test(self, parsed_tests_mapping):
        """ 执行测试 """
        case_summary_list = []
        functions = parsed_tests_mapping.get("project_mapping", {}).get("functions", {})
        for test_case_mapping in parsed_tests_mapping["case_list"]:  # 执行测试用例
            report_case = test_case_mapping["config"]["report_case"]
            case_runner = runner.Runner(test_case_mapping["config"], functions)

            report_case.summary["stat"]["total"] = len(test_case_mapping["step_list"])
            await report_case.test_is_running()

            report_case.summary["time"]["start_at"] = datetime.datetime.now()  # 开始执行用例时间
            for test_step in test_case_mapping["step_list"]:
                try:
                    await case_runner.run_step(test_step)  # 执行测试步骤
                    step_error_traceback = None
                except Exception as error:
                    step_error_traceback = str(error)

                    # 没有执行结果，代表是执行异常，否则代表是步骤里面捕获了异常过后再抛出来的
                    if case_runner.client_session.meta_data["result"] is None:
                        logger.error(traceback.format_exc())
                        case_runner.client_session.meta_data["result"] = "error"

                await case_runner.report_step.save_step_result_and_summary(case_runner, step_error_traceback)
                case_runner.report_step.add_run_step_result_count(
                    report_case.summary, case_runner.client_session.meta_data)

            report_case.summary["time"]["end_at"] = datetime.datetime.now()  # 用例执行结束时间
            case_runner.try_close_browser()  # 执行完一条用例，不管是不是ui自动化，都强制执行关闭浏览器，防止执行时报错，导致没有关闭到浏览器造成driver进程一直存在

            await report_case.save_case_result_and_summary()
            case_summary_list.append(report_case.summary)

        return case_summary_list

    async def run(self, tests_dict):
        """ 执行测试的流程 """

        parsed_test_mapping = await parser.parse_test_data(tests_dict)  # 解析测试计划
        case_summary_list = await self.run_test(parsed_test_mapping)  # 执行测试
        # self.summary = report.merge_test_result(case_summary_list, parsed_test_mapping["report"].summary)  # 汇总测试结果
        self.summary = parsed_test_mapping["report"].merge_test_result(case_summary_list)  # 汇总测试结果
