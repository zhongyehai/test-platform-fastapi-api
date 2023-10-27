import copy
import traceback
from unittest.case import SkipTest

from . import exceptions, response, extract
from utils.client.test_runner.client.http import HttpSession
from utils.client.test_runner.client.webdriver import WebDriverSession
from .runner_context import SessionContext
from .webdriver_action import GetWebDriver, GetAppDriver
from ...redirect_print_log import RedirectPrintLogToMemory


class Runner:
    """ Running testcases.

    Examples:
        >>> functions={...}
        >>> config = {
                "name": "XXXX",
                "base_url": "http://127.0.0.1",
                "verify": False
            }
        >>> runner = Runner(config, functions)

        >>> test_dict = {
                "name": "test description",
                "variables": [],        # optional
                "request": {
                    "url": "http://127.0.0.1:5000/api/users/1000",
                    "method": "GET"
                }
            }
        >>> runner.run_test(test_dict)

    """

    def __init__(self, config, functions, task_type="api"):
        """ 运行测试用例

        Args:
            config (dict): testcase/testsuite config dict

                {
                    "name": "ABC",
                    "variables": {},
                    "setup_hooks", [],
                    "teardown_hooks", []
                }
        """
        self.base_url = config.get("base_url")
        self.run_env = config.get("run_env")
        self.verify = config.get("verify", True)
        self.output = config.get("output", [])
        self.functions = functions
        self.validation_results = []
        self.run_type = config.get("run_type") or "api"
        self.resp_obj = None
        self.driver = None
        self.client_session = None
        self.redirect_print = None

        self.browser_driver_path = config.get("browser_path")
        self.browser_name = config.get("browser_type")
        self.appium_config = config.get("appium_config", {})

        # 记录当前步骤的执行进度
        self.report_step = None
        self.testcase_teardown_hooks = config.get("teardown_hooks", [])  # 用例级别的后置条件

        self.session_context = SessionContext(self.functions)

        self.do_hook_actions(config.get("setup_hooks", []))  # 用例级别的前置条件

    def init_client_session(self):
        """ 根据不同的测试类型获取不同的client_session """
        if self.client_session is None:
            if self.run_type == "api":
                self.client_session = HttpSession(self.base_url)
            elif self.run_type == "webUi":
                self.client_session = WebDriverSession()
                self.driver = GetWebDriver(browser_driver_path=self.browser_driver_path, browser_name=self.browser_name)
            else:
                self.client_session = WebDriverSession()
                self.driver = GetAppDriver(**self.appium_config)

        self.client_session.meta_data["result"] = None  # 开始执行步骤前，把执行结果置为None

    def try_close_browser(self):
        """ 强制关闭浏览器 """
        try:
            self.driver.close_browser()
        except Exception:
            pass

    def __del__(self):
        if self.testcase_teardown_hooks:
            self.do_hook_actions(self.testcase_teardown_hooks)

    def __clear_step_test_data(self):
        """ 清除请求和响应数据 """
        if not isinstance(self.client_session, HttpSession):
            return

        self.validation_results = []
        self.client_session.init_step_meta_data()

    def check_step_is_skip(self, test_dict):
        """ 判断是否跳过当前测试
            - skip: skip current test unconditionally
            - skipIf: skip current test if condition is true
            - skipUnless: skip current test unless condition is true
        Args:
            test_dict (dict): test info
        Raises:
            SkipTest: skip test
        """
        if test_dict.get("skip"):
            raise SkipTest("skip触发跳过此步骤")

        elif test_dict.get("skipIf"):  # 只有 skipIf 条件为结果为True时才跳过，条件为假，或者执行报错，都不跳过
            # [{"expect": 200, "comparator": "_01equals", "check_value": 200, "check_result": "unchecked"}]
            skip_if_condition = self.session_context.eval_content(test_dict["skipIf"])

            for skip_if in skip_if_condition:
                skip_type = skip_if["skip_type"]
                if skip_if["data_source"] == "run_env":
                    skip_if["check_value"] = self.run_env
                try:
                    # 借用断言来判断条件是否为真，满足条件时返回值为None
                    skip_if_res = self.session_context.do_api_validation(skip_if)
                except Exception as error:
                    skip_if_res = error

                # 或，任意一个满足，则跳过
                # 且，任意一个不满足，则跳过
                if (skip_type == "or" and skip_if_res is None) or (skip_type == "and" and skip_if_res is not None):
                    raise SkipTest(f"skipIf触发跳过此步骤 \n{skip_if}")

        elif test_dict.get("skipUnless"):
            skip_unless_condition = test_dict["skipUnless"]
            if not self.session_context.eval_content(skip_unless_condition):
                raise SkipTest(f"skipUnless触发跳过此步骤 \n{skip_unless_condition}")

    def do_hook_actions(self, actions):
        """ 执行前置/后置自定义函数
        Args:
            actions (list):
                格式一，执行完钩子函数后，把返回值保存到变量中 (dict):  {"var": "${func()}"}
                格式二，仅执行函数 (str): ${func()}
        """
        for action in actions:
            if isinstance(action, dict) and len(action) == 1:
                # 第一种格式 {"var": "${func()}"}
                var_name, hook_content = list(action.items())[0]
                hook_content_eval = self.session_context.eval_content(hook_content)
                self.session_context.update_test_variables(var_name, hook_content_eval)
            else:
                # 第二种格式
                self.session_context.eval_content(action)

    async def _run_test(self, step_dict):
        """ 单个测试步骤运行。

        Args:
            step_dict (dict): teststep info
                {
                    "name": "teststep description",
                    "skip": "skip this test unconditionally",
                    "times": 3,
                    "variables": [],            # optional, override
                    "request": {
                        "url": "http://127.0.0.1:5000/api/users/1000",
                        "method": "POST",
                        "headers": {
                            "Content-Type": "application/json",
                            "authorization": "$authorization",
                            "random": "$random"
                        },
                        "json": {"name": "user", "password": "123456"}
                    },
                    "extract": {},              # optional
                    "validate": [],             # optional
                    "setup_hooks": [],          # optional
                    "teardown_hooks": []        # optional
                }

        Raises:
            exceptions.ParamsError
            exceptions.ValidationFailure
            exceptions.ExtractFailure

        """
        self.__clear_step_test_data()
        # self.redirect_print = RedirectPrintLogToMemory()  # 重定向自定义函数的打印到内存中

        test_variables = step_dict.get("variables", {})
        self.session_context.init_test_variables(test_variables)

        self.check_step_is_skip(step_dict)  # 步骤是否满足跳过条件

        # 解析请求，替换变量、自定义函数
        if self.run_type == "api":
            request_data = step_dict.get("request", {})
            # 把上一个步骤提取出来需要更新到头部信息的数据更新到请求上
            request_data["headers"] = self.session_context.update_filed_to_header(request_data["headers"])
        else:
            request_data = step_dict.get("test_action", {})

        parsed_step = self.session_context.eval_content(request_data)
        self.session_context.update_test_variables("request", parsed_step)

        # 如果请求体是字符串（xml），转为utf-8格式
        if parsed_step.get("data") and isinstance(parsed_step["data"], str):
            parsed_step["data"] = parsed_step["data"].encode("utf-8")

        # 执行前置函数
        await self.report_step.test_is_start_before()
        self.do_hook_actions(step_dict.get("setup_hooks", []))

        # 深拷贝除 request 的其他数据，请求数据有可能是io，io不能深拷贝，所以先移出再深拷贝，再移入
        copy_request = self.session_context.test_variables_mapping.pop("request")
        variables_mapping = copy.deepcopy(self.session_context.test_variables_mapping)
        self.session_context.test_variables_mapping["request"] = copy_request

        # 开始执行测试
        await self.report_step.test_is_start_running()
        case_id, step_name, extractors = step_dict.get("case_id"), step_dict.get("name"), step_dict.get("extract", {})
        if self.run_type == "api":
            # 发送请求
            url, method = parsed_step.pop("url"), parsed_step.pop("method")
            parsed_step.setdefault("verify", self.verify)
            resp = self.client_session.request(
                method,
                url,
                name=step_name,
                case_id=case_id,
                variables_mapping=copy.deepcopy(variables_mapping),
                **parsed_step
            )
            self.resp_obj = response.ResponseObject(resp)

            # 数据提取
            await self.report_step.test_is_start_extract()
            extracted_variables_mapping = self.resp_obj.extract_response(
                self.session_context, extractors.get("extractors", []))
            self.session_context.update_test_variables("response", self.resp_obj)
        else:
            # 执行测试步骤浏览器操作
            self.client_session.do_action(
                self.driver,
                name=step_name,
                case_id=case_id,
                variables_mapping=copy.deepcopy(variables_mapping),
                **parsed_step
            )
            # 数据提取
            await self.report_step.test_is_start_extract()
            extracted_variables_mapping = extract.extract_data(self.session_context, self.driver, extractors)

        self.client_session.meta_data["data"][0]["extract_msgs"] = extracted_variables_mapping
        self.session_context.update_session_variables(extracted_variables_mapping)  # 把提取到的数据更新到变量中

        if self.run_type == "api":
            # 把需要更新到头部信息的数据保存下来
            self.session_context.save_update_to_header_filed(
                extractors.get("update_to_header_filed_list", []),
                extracted_variables_mapping
            )

        # 后置函数
        await self.report_step.test_is_start_after(self.get_test_step_data())
        self.do_hook_actions(step_dict.get("teardown_hooks", []))

        # 断言
        await self.report_step.test_is_start_validate()
        validators = step_dict.get("validate", [])
        try:
            self.session_context.validate(
                validators,
                self.run_type,
                resp_obj=self.resp_obj,
                driver=self.driver
            )
        except (exceptions.ParamsError, exceptions.ValidationFailure, exceptions.ExtractFailure):
            raise
        finally:
            self.validation_results = self.session_context.validation_results
            self.client_session.meta_data["data"][0]["validation_results"] = self.validation_results  # 保存断言结果

        await self.report_step.test_is_success(self.get_test_step_data())

    def get_test_step_data(self):
        """ 获取测试数据 """
        request = copy.deepcopy(self.client_session.meta_data["data"][0]["request"])
        request_body = request.get("body")
        if request_body and isinstance(request_body, bytes):
            request["body"] = str(request_body)

        data = {
            "case_id": self.client_session.meta_data.get("case_id"),
            "name": self.client_session.meta_data["name"],
            "stat": self.client_session.meta_data["stat"],
            "redirect_print": self.client_session.meta_data["redirect_print"],
            "variables_mapping": self.client_session.meta_data.get("variables_mapping", {}),
            "attachment": "",
            "request": request,
            "response": self.client_session.meta_data["data"][0]["response"],
            "test_action": self.client_session.meta_data["data"][0].get("test_action"),
            "extract_msgs": self.client_session.meta_data["data"][0].get("extract_msgs", {}),
            "validation_results": self.client_session.meta_data["data"][0].get("validation_results", []),
            "before": self.client_session.meta_data["data"][0].get("before"),
            "after": self.client_session.meta_data["data"][0].get("after")
        }
        return data

    async def run_step(self, step_dict):
        """ 运行用例的单个测试步骤
        Args:
            step_dict (dict):{
                    "name": "teststep description",
                    "variables": [],        # optional
                    "request": {
                        "url": "http://127.0.0.1:5000/api/users/1000",
                        "method": "GET"
                    }
                }
        """
        self.meta_datas = None
        self.redirect_print = RedirectPrintLogToMemory()  # 重定向自定义函数的打印到内存中
        try:
            self.init_client_session()  # 执行步骤前判断有没有初始化client_session
        except Exception as error:
            print(f'初始化执行终端报错：{traceback.format_exc()}')
        self.report_step = step_dict.pop("report_step")

        await self.report_step.test_is_running()
        await self.report_step.test_is_start_parse(step_dict)

        try:
            await self._run_test(step_dict)
            self.client_session.meta_data["result"] = "success"
        except Exception as error:  # 捕获步骤运行中报错(报错、断言不通过、跳过测试)
            # 如果不是跳过测试的异常，则把当前测试用例运行结果标识为失败，后续步骤可根据此状态判断是否继续执行
            if isinstance(error, SkipTest):
                self.client_session.meta_data["result"] = "skip"
                await self.report_step.test_is_skip()
            else:
                self.session_context.update_session_variables({"case_run_result": "fail"})

                if isinstance(error, (
                        exceptions.ParamsError,
                        exceptions.ValidationFailure,
                        exceptions.ExtractFailure,
                        exceptions.ReadTimeout
                )) is False:
                    self.client_session.meta_data["result"] = "error"
                else:
                    self.client_session.meta_data["result"] = "fail"
            raise
        finally:
            # 保存自定义函数的 print 打印, 并把print重定向到默认输出
            self.client_session.meta_data["redirect_print"] = self.redirect_print.get_text_and_redirect_to_default()
