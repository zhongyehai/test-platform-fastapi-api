# # -*- coding: utf-8 -*-
# import datetime
# import platform
# import time
# import unittest
# from base64 import b64encode
#
# try:
#     from collections import Iterable
# except:
#     from collections.abc import Iterable
#
# import requests
#
# from .compat import basestring, json, numeric_types
#
# from app.api_test.models.report import ApiReportStep
#
#
# # from app.app_ui_test.models.report import AppUiReportStep
# # from app.web_ui_test.models.report import WebUiReportStep
#
#
# def get_system_platform():
#     """ 系统信息 """
#     return {
#         "python_version": f"{platform.python_implementation()} {platform.python_version()}",
#         "platform": platform.platform()
#     }
#
#
# def build_case_summary(result):
#     """ 从测试结果中解析成用例级别的详细数据，用于渲染报告
#     Args:
#         result (instance): HtmlTestResult() instance
#     Returns:
#         dict: summary extracted from result.
#             {
#                 "success": True,
#                 "stat": {},
#                 "time": {},
#                 "records": []
#             }
#     """
#     success = result.wasSuccessful()
#     total = result.testsRun
#     failures = result.failures.__len__()
#     errors = result.errors.__len__()
#     skipped = result.skipped.__len__()
#     expected_failures = result.expectedFailures.__len__()
#     unexpected_successes = result.unexpectedSuccesses.__len__()
#
#     return {
#         "success": success,
#         "case_id": None,
#         "project_id": None,
#         "stat": {
#             'total': total,
#             'failures': failures,
#             'errors': errors,
#             'skipped': skipped,
#             'expectedFailures': expected_failures,
#             'unexpectedSuccesses': unexpected_successes,
#             'successes': total - failures - errors - skipped - expected_failures - unexpected_successes
#         },
#         "time": {
#             'start_at': result.start_at,
#             'start_date': datetime.datetime.fromtimestamp(result.start_at).strftime("%Y-%m-%d %H:%M:%S"),
#             'duration': result.duration
#         }
#     }
#
#
# # def init_case_summary(case_summary, test_case_config):
# #     """ 初始化用例统计 """
# #     now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
# #     case_summary["name"] = test_case_config["name"]
# #     case_summary["case_id"] = test_case_config["case_id"]
# #     case_summary["project_id"] = test_case_config["project_id"]
# #
# #     case_summary["time"]["start_at"] = now
# #     case_summary["time"]["start_date"] = now
# #     case_summary["time"]["step_duration"] = 0
# #     case_summary["time"]["case_duration"] = 0
# #
# #     case_summary["stat"]["success"] = 0
# #     case_summary["stat"]["fail"] = 0
# #     case_summary["stat"]["error"] = 0
# #     case_summary["stat"]["skip"] = 0
#
#
# # async def save_case_result_and_summary(report_case, case_summary):
# #     """ 保存测试用例的结果和数据 """
# #     # 耗时
# #     case_summary["time"]["step_duration"] = case_summary["time"]["step_duration"]
# #     if case_summary["time"]["step_duration"] > 0:
# #         case_summary["time"]["case_duration"] = round(case_summary["time"]["step_duration"] / 1000, 4)  # 毫秒转秒
# #     else:
# #         case_summary["time"]["case_duration"] = (case_summary["time"]["end_at"] - case_summary["time"]["start_at"]).total_seconds() * 1000
# #     case_summary["time"]["start_at"] = case_summary["time"]["start_at"].strftime("%Y-%m-%d %H:%M:%S.%f")
# #     case_summary["time"]["end_at"] = case_summary["time"]["end_at"].strftime("%Y-%m-%d %H:%M:%S.%f")
# #
# #     # 状态
# #     if case_summary["stat"]["fail"] or case_summary["stat"]["error"]:  # 步骤里面有不通过或者错误，则把用例的结果置为不通过
# #         case_summary["result"] = "fail"
# #         await report_case.test_is_fail(summary=case_summary)
# #     else:
# #         case_summary["result"] = "success"
# #         await report_case.test_is_success(summary=case_summary)
#
#
# # async def save_step_result_and_summary(step_runner, step_error_traceback=None):
# #     """ 保存测试步骤的结果和数据 """
# #     report_step, step_data = step_runner.report_step, step_runner.get_test_step_data()
# #     step_meta_data = step_runner.client_session.meta_data
# #     step_data["attachment"] = step_error_traceback
# #     # 保存测试步骤的结果和数据
# #     await report_step.update_report_step_data(
# #         step_data=step_data, result=step_meta_data["result"], summary=step_meta_data["stat"])
#
#
# # def add_run_step_result_count(case_summary, step_meta_data):
# #     """ 记录步骤执行结果数量 """
# #     match step_meta_data["result"]:
# #         case "success":
# #             case_summary["stat"]["success"] += 1
# #             case_summary["time"]["step_duration"] += step_meta_data["stat"]["elapsed_ms"]
# #         case "fail":
# #             case_summary["stat"]["fail"] += 1
# #             case_summary["time"]["step_duration"] += step_meta_data["stat"]["elapsed_ms"]
# #         case "error":
# #             case_summary["stat"]["error"] += 1
# #         case "skip":
# #             case_summary["stat"]["skip"] += 1
#
#
# # def merge_test_result(case_summary_list, report_summary):
# #     """ 汇总测试数据和结果
# #     Args:
# #         case_summary_list (list): list of (testcase, result)
# #     """
# #     case_result = []
# #     report_summary["stat"]["test_case"]["total"] = len(case_summary_list)
# #     report_summary["time"]["start_at"] = case_summary_list[0]["time"]["start_at"]
# #     report_summary["time"]["start_date"] = case_summary_list[0]["time"]["start_date"]
# #     for case_summary in case_summary_list:
# #         case_result.append(case_summary["result"])
# #         report_summary["stat"]["test_case"][case_summary["result"]] += 1
# #         report_summary["stat"]["test_step"]["total"] += case_summary["stat"]["total"]
# #         report_summary["stat"]["test_step"]["fail"] += case_summary["stat"]["fail"]
# #         report_summary["stat"]["test_step"]["error"] += case_summary["stat"]["error"]
# #         report_summary["stat"]["test_step"]["skip"] += case_summary["stat"]["skip"]
# #         report_summary["stat"]["test_step"]["success"] += case_summary["stat"]["success"]
# #         report_summary["time"]["step_duration"] += case_summary["time"]["step_duration"]
# #         report_summary["time"]["case_duration"] += case_summary["time"]["case_duration"]
# #
# #     report_summary["result"] = "error" if "error" in case_result else "fail" if "fail" in case_result else "success"
# #     return report_summary
#
#
# def merge_stat(origin_stat, new_stat):
#     """ 合并stat """
#     for key in new_stat:
#         if key not in origin_stat:
#             origin_stat[key] = new_stat[key]
#         elif key == "start_at":
#             origin_stat[key] = min(origin_stat[key], new_stat[key])
#         else:
#             origin_stat[key] += new_stat[key]
#
#
# # def format_summary(summary):
# #     """ 格式化测试结果数据，以便转储json文件并生成html报告。 """
# #     for index, suite_summary in enumerate(summary["details"]):
# #
# #         if not suite_summary.get("name"):
# #             suite_summary["name"] = "testcase {}".format(index)
# #
# #         # for meta_data in suite_summary.get("records"):
# #         #     format_meta_data(meta_data)
#
#
# def format_request(request_data: dict):
#     """ 格式化http请求数据
#     Args:
#         request_data (dict): HTTP request data in dict.
#
#             {
#                 "url": "http://127.0.0.1:5000/api/get-token",
#                 "method": "POST",
#                 "headers": {
#                     "User-Agent": "python-requests/2.20.0",
#                     "Accept-Encoding": "gzip, deflate",
#                     "Accept": "*/*",
#                     "Connection": "keep-alive",
#                     "user_agent": "iOS/10.3",
#                     "device_sn": "TESTCASE_CREATE_XXX",
#                     "os_platform": "ios",
#                     "app_version": "2.8.6",
#                     "Content-Type": "application/json",
#                     "Content-Length": "52"
#                 },
#                 "json": {
#                     "sign": "cb9d60acd09080ea66c8e63a1c78c6459ea00168"
#                 },
#                 "verify": false
#             }
#
#     """
#     for key, value in request_data.items():
#
#         if isinstance(value, list):
#             value = json.dumps(value, indent=2, ensure_ascii=False)
#
#         elif isinstance(value, bytes):
#             try:
#                 encoding = "utf-8"
#                 value = escape(value.decode(encoding))
#             except UnicodeDecodeError:
#                 pass
#
#         elif not isinstance(value, (basestring, numeric_types, Iterable)):
#             # class instance, e.g. MultipartEncoder()
#             value = repr(value)
#
#         elif isinstance(value, requests.cookies.RequestsCookieJar):
#             value = value.get_dict()
#
#         request_data[key] = value
#
#
# def format_response(response_data: dict):
#     """ 格式化http响应数据
#     Args:
#         response_data:
#             {
#                 "status_code": 404,
#                 "headers": {
#                     "Content-Type": "application/json",
#                     "Content-Length": "30",
#                     "Server": "Werkzeug/0.14.1 Python/3.7.0",
#                     "Date": "Tue, 27 Nov 2018 06:19:27 GMT"
#                 },
#                 "encoding": "None",
#                 "content_type": "application/json",
#                 "ok": false,
#                 "url": "http://127.0.0.1:5000/api/users/9001",
#                 "reason": "NOT FOUND",
#                 "cookies": {},
#                 "json": {
#                     "success": false,
#                     "data": {}
#                 }
#             }
#     """
#     for key, value in response_data.items():
#
#         if isinstance(value, list):
#             value = json.dumps(value, indent=2, ensure_ascii=False)
#
#         elif isinstance(value, bytes):
#             try:
#                 encoding = response_data.get("encoding")
#                 if not encoding or encoding == "None":
#                     encoding = "utf-8"
#
#                 if key == "content" and "image" in response_data["content_type"]:
#                     # display image
#                     value = "data:{};base64,{}".format(
#                         response_data["content_type"],
#                         b64encode(value).decode(encoding)
#                     )
#                 else:
#                     value = escape(value.decode(encoding))
#             except UnicodeDecodeError:
#                 pass
#
#         elif not isinstance(value, (basestring, numeric_types, Iterable)):
#             # class instance, e.g. MultipartEncoder()
#             value = repr(value)
#
#         elif isinstance(value, requests.cookies.RequestsCookieJar):
#             value = value.get_dict()
#
#         response_data[key] = value
#
#
# def expand_meta_data(meta_data, meta_data_expanded):
#     """ 扩展另一个列表中的字典
#     Args:
#         meta_data: [[dict1, dict2], dict3]
#         meta_data_expanded: []
#     Returns:
#         [dict1, dict2, dict3]
#     """
#     if isinstance(meta_data, dict):
#         meta_data_expanded.append(meta_data)
#     elif isinstance(meta_data, list):
#         for meta_data in meta_data:
#             expand_meta_data(meta_data, meta_data_expanded)
#
#
# def __get_total_response_time(meta_data_expanded):
#     """ 计算所有元数据的总响应时间 """
#     try:
#         response_time = 0
#         for meta_data in meta_data_expanded:
#             response_time += meta_data["stat"]["response_time_ms"]
#
#         return "{:.2f}".format(response_time)
#
#     except TypeError:
#         # failure exists
#         return "N/A"
#
#
# def format_meta_data(meta_data):
#     if isinstance(meta_data, list):
#         for _meta_data in meta_data:
#             format_meta_data(_meta_data)
#     elif isinstance(meta_data, dict):
#         data_list = meta_data["data"]
#         for data in data_list:
#             format_request(data["request"])
#             format_response(data["response"])
#
#
# class HtmlTestResult(unittest.TextTestResult):
#     """ 生成渲染html报告需要的测试结果数据 """
#
#     def __init__(self, stream, descriptions, verbosity):
#         super(HtmlTestResult, self).__init__(stream, descriptions, verbosity)
#         self.start_at = None
#         self.records = []
#
#     def _save_test_data(self, test, attachment=''):
#         """ 在记录的测试步骤数据中，加上attachment """
#         run_type = test.meta_datas.get("run_type")
#         if run_type == "api":
#             report_step_model = ApiReportStep
#         elif run_type == "webUi":
#             report_step_model = WebUiReportStep
#         else:
#             report_step_model = AppUiReportStep
#
#         report_step = report_step_model.get_first(id=test.meta_datas.get("report_step_id"))
#         step_data = json.loads(report_step.step_data)
#         step_data["attachment"] = attachment
#         report_step.update_report_step_data(step_data)
#
#     def _record_test(self, test, status, attachment=''):
#         """ 添加测试步骤的测试结果到报告里面 """
#         self._save_test_data(test, attachment)
#         self.records.append({
#             'name': test.shortDescription(),
#             'status': status,
#             'attachment': attachment,
#             'stat': test.meta_datas.get("stat", {}),
#             'case_id': test.meta_datas.get("case_id", None),
#             'report_step_id': test.meta_datas.get("report_step_id", None),
#             # "meta_datas": test.meta_datas  # 减小内存占用，只记录执行概要信息，详细内容需根据id查询
#         })
#
#     def startTestRun(self):
#         """ 测试开始时间 """
#         self.start_at = time.time()  # 时间戳格式，用于计算
#
#     def startTest(self, test):
#         """ 添加开始测试时间 """
#         super(HtmlTestResult, self).startTest(test)
#
#     def addSuccess(self, test):
#         """ 成功的用例 """
#         super(HtmlTestResult, self).addSuccess(test)
#         self._record_test(test, 'success')
#         print("")
#
#     def addError(self, test, err):
#         """ 错误的用例 """
#         super(HtmlTestResult, self).addError(test, err)
#         self._record_test(test, 'error', self._exc_info_to_string(err, test))
#         print("")
#
#     def addFailure(self, test, err):
#         """ 失败的用例 """
#         super(HtmlTestResult, self).addFailure(test, err)
#         self._record_test(test, 'fail', self._exc_info_to_string(err, test))
#         print("")
#
#     def addSkip(self, test, reason):
#         """ 跳过的用例 """
#         super(HtmlTestResult, self).addSkip(test, reason)
#         self._record_test(test, 'skip', reason)
#         print("")
#
#     # def addExpectedFailure(self, test, err):
#     #     super(HtmlTestResult, self).addExpectedFailure(test, err)
#     #     self._record_test(test, 'ExpectedFailure', self._exc_info_to_string(err, test))
#     #     print("")
#     #
#     # def addUnexpectedSuccess(self, test):
#     #     super(HtmlTestResult, self).addUnexpectedSuccess(test)
#     #     self._record_test(test, 'UnexpectedSuccess')
#     #     print("")
#
#     @property
#     def duration(self):
#         """ 用例耗时 """
#         return round(time.time() - self.start_at, 4)
