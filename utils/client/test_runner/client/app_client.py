# -*- coding: utf-8 -*-
import os
import time
import json
import base64
import asyncio
import subprocess
import traceback
from datetime import datetime
from functools import partial
from unittest.case import SkipTest
from concurrent.futures import ThreadPoolExecutor
from typing import Tuple, Dict, List, Any, Optional, Union

from appium import webdriver
from appium.options.common import AppiumOptions
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import (
    TimeoutException,
    WebDriverException,
    NoSuchElementException,
    ElementNotVisibleException,
    ElementNotInteractableException,
    InvalidSessionIdException,
)
from urllib3.exceptions import ProtocolError

from utils.client.test_runner.client.base_client import BaseSession, BaseClient
from utils.client.test_runner.exceptions import RunTimeException  # TimeoutException,
from utils.util.file_util import FileUtil


class APPClientSession(BaseSession):
    """ 实例化页面执行器上下文 """

    async def async_do_action(self, client, name=None, case_id=None, variables_mapping={}, **kwargs):
        """ 执行操作, 为了通用性，封装为异步方式 """
        kwargs.update(dict(client=client, name=name, case_id=case_id, variables_mapping=variables_mapping))
        max_workers = min(50, os.cpu_count() * 5)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            try:
                bound_func = partial(self.do_appium_action, *(), **kwargs)
                return await asyncio.get_running_loop().run_in_executor(executor, bound_func)
            except Exception as e:
                raise

    @classmethod
    def save_screenshot_by_appium(cls, client, save_path):
        """ 保存 Appium 截图（无需 await） """
        base64_screenshot = client.get_screenshot_as_base64()
        FileUtil.save_file(save_path, base64_screenshot)

    def do_appium_action(self, client, name=None, case_id=None, variables_mapping=None, **kwargs):
        variables_mapping = variables_mapping or {}
        report_img_folder, report_step_id = kwargs.pop("report_img_folder"), kwargs.pop("report_step_id")

        self._record_meta_data(name, case_id, variables_mapping, kwargs)

        # 执行前截图（调用 App 客户端的同步方法，无 await）
        before_save_path = self.get_screenshot_save_path(report_img_folder, report_step_id, is_before=True)
        self.save_screenshot_by_appium(client, before_save_path)

        # 执行测试步骤
        start_at = datetime.now()
        result = self._do_appium_action(client, **kwargs)
        end_at = datetime.now()

        # 执行后截图
        after_save_path = self.get_screenshot_save_path(report_img_folder, report_step_id, is_before=False)
        self.save_screenshot_by_appium(client, after_save_path)

        # 记录耗时
        self._record_elapsed_time(start_at, end_at)
        return result

    @classmethod
    def _do_appium_action(cls, client, **kwargs):
        try:
            action_name = kwargs.get('action')
            action_func = getattr(client, action_name)

            if action_name == 'get_screenshot_as_base64':
                return action_func()  # 移除 await
            else:
                wait_time_out = kwargs.get('wait_time_out')
                run_action = action_func(
                    locator=(kwargs.get('by_type'), kwargs.get('element')),
                    text=kwargs.get('text'),
                    screen=kwargs.get('screen'),
                    wait_time_out=wait_time_out
                )
                return run_action
        except NoSuchElementException as e:
            raise RunTimeException(f'appium元素未找到：{str(e)}\n'
                                   f'解决方案：1. 用 Appium Inspector 验证元素选择器（id/xpath/class 等）；2. 延长隐式/显式等待时间；3. 确认页面是否正常跳转')
        except TimeoutException as e:
            error = str(e)
            if 'An element could not be located on the page using the given search parameters.' in error:
                raise RunTimeException(f'appium元素未找到：{str(e)}\n'
                                       f'解决方案：1. 用 Appium Inspector 验证元素选择器（id/xpath/class 等）；2. 延长隐式/显式等待时间；3. 确认页面是否正常跳转')
            raise RunTimeException(f'appium执行超时：{str(e)}\n'
                                   f'解决方案：1. 延长 `implicitly_wait()` 或显式等待时间；2. 检查 Appium Server 是否稳定；3. 优化设备性能（避免卡顿）')
        except ElementNotInteractableException as e:
            raise RunTimeException(f'appium元素不可操作：{str(e)}\n'
                                   f'解决方案：1. 检查元素是否被弹窗/其他控件遮挡；2. 验证元素是否处于启用状态（disabled=false）；3. 等待元素完全渲染后再操作')
        except ElementNotVisibleException as e:
            raise RunTimeException(f'appium元素不可见：{str(e)}\n'
                                   f'解决方案：1. 滑动页面将元素带入可视区域；2. 检查元素是否被设置为隐藏（display:none）；3. 确认是否在正确的页面')
        except InvalidSessionIdException as e:
            raise RunTimeException(f'Appium 会话已断开：{str(e)}\n'
                                   f'解决方案：1. 检查 Appium Server 是否仍在运行；2. 延长 `newCommandTimeout` 配置；3. 避免长时间无操作，必要时重新建立会话')
        except WebDriverException as e:
            raise RunTimeException(f'Appium 初始化失败：{str(e)}\n'
                                   f'解决方案：1. 检查 Appium Server 是否已启动（命令：appium）；2. 验证 desired_capabilities 配置（包名/Activity/系统版本）；3. 检查设备是否正常连接（adb devices）；4. 确认应用已安装在设备上')
        except ProtocolError as e:
            raise RunTimeException(f'Appium 客户端与服务端通信中断：{str(e)}\n'
                                   f'排查顺序：appium server 是否启动 → 验证设备是否已连接 → 检查版本兼容 → 关闭防火墙')
        except Exception as e:
            if isinstance(e, SkipTest):
                 raise
            else:
                raise RunTimeException(f'未知运行时异常，请检查:\n{traceback.print_exc()}')


class AppClient(BaseClient):
    """ appium对象管理 """

    def __init__(self, **kwargs):
        """
        获取appium操作对象
        参数示例（kwargs）：
        {
            "platformName": "iOS" / "Android",
            "platformVersion": "14.5",
            "deviceName": "iPhone Simulator" / "Android Emulator",
            "appPackage": "com.taobao.taobao",
            "appActivity": "com.taobao.tao.TBMainActivity",
            "noReset": True,
            "automationName": "UiAutomator2" / "XCUITest"
        }
        """
        self.wait_time_out = 5  # 默认超时时间（秒）
        # 提取appium服务配置
        self.host = kwargs.pop('host', '127.0.0.1')
        self.port = kwargs.pop('port', 4723)
        self.remote_path = kwargs.pop('remote_path', '/wd/hub')
        try:
            self.options = AppiumOptions()
            for key, value in kwargs.items():
                self.options.set_capability(key, value)

            # 初始化appium driver（新版本兼容）
            self.driver = webdriver.Remote(
                command_executor=f'http://{self.host}:{self.port}{self.remote_path}',
                options=self.options
            )
        except Exception as error:
            # 补充异常提示信息，便于排查
            raise Exception(
                f"Appium 初始化失败：{str(error)}（请检查服务是否启动、设备是否连接、配置是否正确）") from error

    async def close_all(self):
        """ 关闭app并退出driver """
        try:
            if hasattr(self, 'driver') and self.driver:
                self.driver.quit()
            print("app 关闭成功")
        except Exception as e:
            print(f"app 关闭失败：{e}")

    @property
    def width(self):
        """ 获取手机屏幕宽度 """
        size = self.driver.get_window_size()
        size_width = size.get('width', size.get('w', 0))
        print(f'width: {size_width}')
        return size_width

    @property
    def height(self):
        """ 获取屏幕高度 """
        size = self.driver.get_window_size()
        size_height = size.get('height', size.get('h', 0))
        print(f'size_height: {size_height}')
        return size_height

    def web_driver_wait_until(self, *args, **kwargs):
        """ 基于 WebDriverWait().until()封装base方法 """
        return WebDriverWait(self.driver, kwargs.get('wait_time_out', self.wait_time_out), 1).until(*args)

    def find_element(self, locator: Tuple[str, str], wait_time_out: Optional[int] = None, **kwargs) -> Any:
        """
        定位一个元素
        参数：locator是元组类型，(定位方式, 定位元素)，如('id', 'username')
        支持定位方式：id、xpath、className、coordinate（坐标）等
        更多定位方式见：appium.webdriver.common.appiumby.AppiumBy
        """

        return self.web_driver_wait_until(
            ec.presence_of_element_located(locator), wait_time_out=wait_time_out
        )

    def find_elements(self, locator: Tuple[str, str], wait_time_out: Optional[int] = None, **kwargs) -> List[Any]:
        """
        定位一组元素
        更多定位方式见：appium.webdriver.common.appiumby.AppiumBy
        """
        return self.web_driver_wait_until(
            ec.presence_of_all_elements_located(locator), wait_time_out=wait_time_out or self.wait_time_out
        )

    #################################### 点击相关事件 ####################################
    def action_01_01_click(
            self, locator: Tuple[str, str], text: str = '', wait_time_out: Optional[int] = None, **kwargs):
        """ 【点击】直接点击元素 """
        if locator[0] == 'coordinate':  # 坐标定位
            try:
                coordinate = eval(locator[1])
                # 确保坐标为非负整数
                x, y = int(coordinate[0]), int(coordinate[1])
                x = max(0, min(x, self.width))
                y = max(0, min(y, self.height))

                self.driver.tap([(x, y)], duration=100)
            except Exception as e:
                raise Exception(f"坐标点击失败：{str(e)}") from e
        else:  # 元素定位
            element = self.find_element(locator, wait_time_out=wait_time_out)
            element.click()

    def action_01_02_click_if_has_element(
            self, locator: Tuple[str, str], text: str = '', wait_time_out: Optional[int] = None, **kwargs):
        """ 【点击】元素存在就点击 """
        if locator[0] == 'coordinate':  # 坐标定位
            coordinate = eval(locator[1])
            x, y = int(coordinate[0]), int(coordinate[1])
            self.driver.tap([(x, y)], duration=100)
        else:  # 元素定位
            try:
                element = self.find_element(locator, wait_time_out=wait_time_out)
            except Exception:
                raise SkipTest(f"【元素存在就点击】元素未找到，触发跳过")
            if element:
                element.click()

    def action_01_05_click_alert_dismiss(self, locator: Tuple[str, str], **kwargs):
        """ 【点击】点击坐标（APP），locator = ("bounds","[[918,1079], [1080,1205]]")，kwargs={"screen": "1920x1080"} """
        try:
            bounds = json.loads(locator[1])  # 格式：[[918,1079], [1080,1205]]
            bounds1, bounds2 = bounds[0], bounds[1]
            x1, y1, x2, y2 = bounds1[0], bounds1[1], bounds2[0], bounds2[1]

            # 模板设备分辨率适配
            screen = kwargs.get("screen")
            if screen:
                screen_list = screen.lower().split("x")
                if len(screen_list) != 2:
                    raise ValueError("screen参数格式错误，应为：1920x1080")
                screen_width, screen_height = int(screen_list[0]), int(screen_list[1])

                # 按比例换算当前设备坐标
                if screen_width != self.width or screen_height != self.height:
                    x1 = x1 / screen_width * self.width
                    y1 = y1 / screen_height * self.height
                    x2 = x2 / screen_width * self.width
                    y2 = y2 / screen_height * self.height

            # 计算元素中心坐标并点击
            center_x = (x1 + x2) / 2
            center_y = (y1 + y2) / 2
            self.driver.tap([(center_x, center_y)], duration=100)
        except Exception as e:
            raise Exception(f"Bounds点击失败：{str(e)}") from e

    #################################### 输入相关事件 ####################################
    def action_02_01_clear_and_send_keys_is_input(
            self, locator: Tuple[str, str], text: str = '', wait_time_out: Optional[int] = None, **kwargs):
        """ 【输入】清空后输入 """
        element = self.find_element(locator, wait_time_out=wait_time_out)
        element.clear()
        element.send_keys(text)

    def action_02_02_click_and_clear_and_send_keys_is_input(
            self, locator: Tuple[str, str], text: str = '', wait_time_out: Optional[int] = None, **kwargs):
        """ 【输入】点击并清空后输入 """
        element = self.find_element(locator, wait_time_out=wait_time_out)
        element.click()
        element.clear()
        element.send_keys(text)

    def action_02_03_send_keys_is_input(
            self, locator: Tuple[str, str], text: str = '', wait_time_out: Optional[int] = None, **kwargs):
        """ 【输入】追加输入 """
        element = self.find_element(locator, wait_time_out=wait_time_out)
        element.send_keys(text)

    def action_02_04_click_and_send_keys_is_input(
            self, locator: Tuple[str, str], text: str = '', wait_time_out: Optional[int] = None, **kwargs):
        """ 【输入】点击并追加输入 """
        element = self.find_element(locator, wait_time_out=wait_time_out)
        element.click()
        element.send_keys(text)

    def action_02_05_send_keys_by_keyboard_is_input(
            self, locator: Tuple[str, str], text: str = '', wait_time_out: Optional[int] = None, **kwargs):
        """ 【输入】模拟键盘输入，locator = ("id","xxx")，send_keys(locator, text)， is_input标识为输入内容 """
        try:
            key_code = int(text)
            self.driver.press_keycode(key_code)
        except ValueError:
            raise ValueError("press_keycode 需传入整数键码，如 66（回车），不支持普通字符串")

    def action_02_06_click_and_send_keys_by_keyboard_is_input(
            self, locator: Tuple[str, str], text: str = '', wait_time_out: Optional[int] = None, **kwargs):
        """ 【输入】点击并模拟键盘输入，locator = ("id","xxx")，send_keys(locator, text)， is_input标识为输入内容 """
        element = self.find_element(locator, wait_time_out=wait_time_out)
        element.click()
        self.action_02_05_send_keys_by_keyboard_is_input(locator, text, wait_time_out)

    def action_02_07_clear_and_send_keys_if_exist_is_input(
            self, locator: Tuple[str, str], text: str = '', wait_time_out: Optional[int] = None, **kwargs):
        """ 【输入】元素存在则清空后输入，locator = ("id","xxx")，send_keys(locator, text)， is_input标识为输入内容 """
        try:
            element = self.find_element(locator, wait_time_out=wait_time_out)
        except Exception:
            raise SkipTest(f"【元素存在则清空后输入】元素未找到，触发跳过")
        element.clear()
        element.send_keys(text)

    def action_02_08_click_clear_and_send_keys_if_exist_is_input(
            self, locator: Tuple[str, str], text: str = '', wait_time_out: Optional[int] = None, **kwargs):
        """ 【输入】元素存在则点击并清空后输入 """
        try:
            element = self.find_element(locator, wait_time_out=wait_time_out)
        except Exception:
            raise SkipTest(f"【元素存在则点击并清空后输入】元素未找到，触发跳过")
        element.click()
        element.clear()
        element.send_keys(text)

    def action_02_09_send_keys_if_exist_is_input(
            self, locator: Tuple[str, str], text: str = '', wait_time_out: Optional[int] = None, **kwargs):
        """ 【输入】元素存在则追加输入 """
        try:
            element = self.find_element(locator, wait_time_out=wait_time_out)
        except Exception:
            raise SkipTest(f"【元素存在则追加输入】元素未找到，触发跳过")
        element.send_keys(text)

    def action_02_10_click_send_keys_if_exist_is_input(
            self, locator: Tuple[str, str], text: str = '', wait_time_out: Optional[int] = None, **kwargs):
        """ 【输入】元素存在则点击并追加输入 """
        try:
            element = self.find_element(locator, wait_time_out=wait_time_out)
        except Exception:
            raise SkipTest(f"【元素存在则点击并追加输入】元素未找到，触发跳过")
        element.click()
        element.send_keys(text)

    #################################### 滚动相关事件 ####################################
    def action_04_01_js_scroll_top(self, **kwargs):
        """ 【滚动】滚动到浏览器/H5顶部 """
        self.driver.execute_script("window.scrollTo(0, 0)")

    def action_04_02_js_scroll_end(self, **kwargs):
        """ 【滚动】滚动到浏览器/H5底部 """
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")

    def action_04_04_app_scroll_coordinate_is_input1(self, conf: Dict = {}, **kwargs):
        """ 【滚动】滚动到手机指定坐标（相对位置）
        conf: {
            "x1": 0.2, "y1": 0.7, "x2": 0.1, "y2": 0.4, "duration": 1000
        }
        """
        x1 = self.width * float(conf.get("x1", 0.5))
        y1 = self.height * float(conf.get("y1", 0.75))
        x2 = self.width * float(conf.get("x2", 0.5))
        y2 = self.height * float(conf.get("y2", 0.25))
        duration = int(conf.get("duration", 1000))

        # 确保坐标合法
        x1, x2 = max(0, x1), max(0, x2)
        y1, y2 = max(0, y1), max(0, y2)

        self.driver.swipe(x1, y1, x2, y2, duration)

    def action_04_05_app_scroll_coordinate_is_input2(self, conf: Dict = {}, **kwargs):
        """ 【滚动】滚动到手机指定坐标（绝对位置）
        conf: {
            "x1": 500, "y1": 1000, "x2": 600, "y2": 1024
        }
        """
        x1 = float(conf.get("x1", 500))
        y1 = float(conf.get("y1", 1000))
        x2 = float(conf.get("x2", 600))
        y2 = float(conf.get("y2", 1024))

        # 确保坐标不超过屏幕范围
        x1, x2 = max(0, min(x1, self.width)), max(0, min(x2, self.width))
        y1, y2 = max(0, min(y1, self.height)), max(0, min(y2, self.height))

        self.driver.swipe(x1, y1, x2, y2, 1000)

    def action_04_06_app_scroll_to_bottom_recursive(self, **kwargs):
        """ 【滚动】递归滚动到手机底部 """
        before_swipe = self.driver.page_source  # 滚动前的页面资源
        self.action_04_04_app_scroll_coordinate_is_input1({"y1": 0.75, "y2": 0.25, "duration": 200})
        after_swipe = self.driver.page_source  # 滚动后的页面资源

        if before_swipe != after_swipe:  # 如果滚动前和滚动后的页面不一致，说明进行了滚动，则继续滚动，否则证明已经滚动到底，不再滚动
            self.action_04_06_app_scroll_to_bottom_recursive()

    def action_04_07_app_scroll_coordinate_end(self, **kwargs):
        """ 【滚动】往上滑动一页 """
        self.driver.swipe(self.width * 0.5, self.height * 0.9, self.width * 0.5, self.height * 0.2, 1500)

    def action_04_08_app_scroll_coordinate_end_is_input(self, text: str = '', **kwargs):
        """ 【滚动】往上滑动指定百分比 """
        try:
            percent = float(text)
            if not 0 < percent < 1:
                raise ValueError("百分比需为0-1之间的小数")
            self.driver.swipe(self.width * 0.5, self.height * 0.9, self.width * 0.5, self.height * (1 - float(text)),
                              1500)
        except ValueError as e:
            raise Exception(f"滑动百分比参数错误：{str(e)}") from e

    def action_04_09_app_scroll_coordinate_end(self, *args, **kwargs):
        """ 【滚动】往下滑动一页（app） """
        self.driver.swipe(self.width * 0.5, self.height * 0.1, self.width * 0.5, self.height * 0.9, 1500)

    def action_04_10_app_scroll_down_by_percent_is_input(self, text: str = '', **kwargs):
        """ 【滚动】往下滑动指定百分比 """
        try:
            percent = float(text)
            if not 0 < percent < 1:
                raise ValueError("百分比需为0-1之间的小数")
            self.driver.swipe(self.width * 0.5, self.height * (1 - float(text)), self.width * 0.5, self.height * 0.9,
                              1500)
        except ValueError as e:
            raise Exception(f"滑动百分比参数错误：{str(e)}") from e

    #################################### 切换相关事件 ####################################
    def action_05_05_switch_to_h5(self, locator: Tuple[str, str], **kwargs):
        """ 【切换-app】切换到H5 """
        try:
            contexts = self.driver.contexts
            print(f"当前可用上下文：{contexts}")
            # H5上下文通常是 WEBVIEW_ 开头，优先选择非NATIVE_APP的上下文
            h5_context = next((ctx for ctx in contexts if "WEBVIEW" in ctx), contexts[-1])
            self.driver.switch_to.context(h5_context)
        except Exception as e:
            raise Exception(f"H5上下文切换失败：{str(e)}") from e

    def action_05_06_switch_to_app(self, locator: Tuple[str, str], **kwargs):
        """ 【切换-app】切换到原生App """
        try:
            contexts = self.driver.contexts
            print(f"当前可用上下文：{contexts}")
            # 切换回原生App上下文
            native_context = next((ctx for ctx in contexts if "NATIVE_APP" in ctx), contexts[0])
            self.driver.switch_to.context(native_context)
        except Exception as e:
            raise Exception(f"原生App上下文切换失败：{str(e)}") from e

    #################################### 上传相关事件 ####################################
    def action_09_01_app_upload_file_is_upload(
            self, locator, file_path: str, wait_time_out: Optional[int] = None, **kwargs):
        """ 【上传】APP上传文件 """
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"文件不存在：{file_path}")
            with open(file_path, 'rb') as f:
                content = f.read()
            # 推送文件到设备
            self.driver.push_file(file_path, base64.b64encode(content).decode('utf-8'))
        except Exception as e:
            raise Exception(f"APP文件上传失败：{str(e)}") from e

    #################################### 辅助相关事件 ####################################
    def action_11_01_sleep_is_input(
            self, locator: Tuple[str, str], time_seconds: Union[int, float, str], wait_time_out: Optional[int] = None,
            **kwargs):
        """ 【辅助】等待指定时间 """
        time.sleep(float(time_seconds) if isinstance(time_seconds, str) else time_seconds)

    def action_11_02_nothing_to_do(self, **kwargs):
        """ 【辅助】不操作元素 """
        return

    def action_11_03_reboot_app(self, **kwargs):
        """ 【辅助】重启APP """
        self.driver.reset()

    def action_11_03_01_close_app_to_background(self, **kwargs):
        """ 【辅助】将应用置于后台 """
        self.driver.close_app()

    def action_11_03_02_quit_app(self, **kwargs):
        """ 【辅助】关闭APP """
        self.driver.quit()

    def action_11_04_reboot_device(self, **kwargs):
        """ 【辅助】使用 adb 命令重启设备 """
        try:
            subprocess.run(['adb', 'reboot'], check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            raise Exception(f"ADB设备重启失败：{str(e)}") from e

    #################################### 数据提取相关事件 ####################################
    def extract_08_title(self, **kwargs):
        """ 获取title """
        return self.driver.title

    def extract_09_text(self, locator: Tuple[str, str], wait_time_out: Optional[int] = None, **kwargs):
        """ 获取文本 """
        element = self.find_element(locator, wait_time_out=wait_time_out)
        return element.text

    def extract_09_value(self, locator: Tuple[str, str], wait_time_out: Optional[int] = None, **kwargs):
        """ 获取value值 """
        element = self.find_element(locator, wait_time_out=wait_time_out)
        return element.get_attribute('value')

    def extract_10_attribute_is_input(
            self, locator: Tuple[str, str], name: str, wait_time_out: Optional[int] = None, **kwargs):
        """ 获取指定属性 """
        element = self.find_element(locator, wait_time_out=wait_time_out)
        return element.get_attribute(name)

    def assert_50str_in_value(self, locator: Tuple[str, str], value: str, **kwargs):
        """ 断言：元素value值包含指定内容 """
        expect_value = self.extract_09_value(locator)
        assert value in expect_value, f"断言失败：实际值「{expect_value}」不包含预期值「{value}」"

    def assert_51_element_value_equal_to(self, locator: Tuple[str, str], content: Any, **kwargs):
        """ 断言：元素value值等于指定内容 """
        expect_value = self.extract_09_value(locator)
        assert expect_value == content, f"断言失败：实际值「{expect_value}」不等于预期值「{content}」"

    def assert_52_element_value_larger_than(self, locator: Tuple[str, str], content: Union[int, float], **kwargs):
        """ 断言：元素value值大于指定数值 """
        expect_value = self.extract_09_value(locator)
        try:
            assert float(expect_value) > float(content), f"断言失败：实际值「{expect_value}」不大于预期值「{content}」"
        except ValueError:
            raise ValueError("元素value值和预期值均需为可转换为浮点数的内容")

    def assert_53_element_value_smaller_than(self, locator: Tuple[str, str], content: Union[int, float],
                                             **kwargs):
        """ 断言：元素value值小于指定数值 """
        expect_value = self.extract_09_value(locator)
        try:
            assert float(expect_value) < float(content), f"断言失败：实际值「{expect_value}」不小于预期值「{content}」"
        except ValueError:
            raise ValueError("元素value值和预期值均需为可转换为浮点数的内容")

    def assert_54is_selected_be(self, locator: Tuple[str, str], wait_time_out: Optional[int] = None, **kwargs):
        """ 断言：元素被选中 """
        is_selected = self.web_driver_wait_until(
            ec.element_located_selection_state_to_be(locator, True),
            wait_time_out=wait_time_out or self.wait_time_out
        )
        assert is_selected, "断言失败：元素未被选中"

    def assert_55is_not_selected_be(
            self, locator: Tuple[str, str], wait_time_out: Optional[int] = None, **kwargs):
        """ 断言：元素未被选中 """
        is_not_selected = self.web_driver_wait_until(
            ec.element_located_selection_state_to_be(locator, False),
            wait_time_out=wait_time_out or self.wait_time_out
        )
        assert is_not_selected, "断言失败：元素已被选中"

    def assert_56_element_txt_equal_to(self, locator: Tuple[str, str], content: Any, **kwargs):
        """ 断言：元素txt值等于指定内容 """
        expect_value = self.extract_09_text(locator)
        assert expect_value == content, f"断言失败：实际值「{expect_value}」不等于预期值「{content}」"

    def assert_56_element_txt_larger_than(self, locator: Tuple[str, str], content: Union[int, float], **kwargs):
        """ 断言：元素txt值大于指定数值 """
        expect_value = self.extract_09_text(locator)
        try:
            assert float(expect_value) > float(content), f"断言失败：实际值「{expect_value}」不大于预期值「{content}」"
        except ValueError:
            raise ValueError("元素txt值和预期值均需为可转换为浮点数的内容")

    def assert_56_element_txt_smaller_than(self, locator: Tuple[str, str], content: Union[int, float], **kwargs):
        """ 断言：元素txt值小于指定数值 """
        expect_value = self.extract_09_text(locator)
        try:
            assert float(expect_value) < float(content), f"断言失败：实际值「{expect_value}」不小于预期值「{content}」"
        except ValueError:
            raise ValueError("元素txt值和预期值均需为可转换为浮点数的内容")

    def assert_57text_in_element(self, locator: Tuple[str, str], text: str, **kwargs):
        """ 断言：元素txt值包含指定内容 """
        expect_value = self.extract_09_text(locator)
        assert text in expect_value, f"断言失败：实际值「{expect_value}」不包含预期值「{text}」"

    def assert_58is_visibility(self, locator: Tuple[str, str], wait_time_out: Optional[int] = None, **kwargs):
        """ 断言：元素可见 """
        is_visible = self.web_driver_wait_until(
            ec.visibility_of_element_located(locator),
            wait_time_out=wait_time_out or self.wait_time_out
        )
        assert is_visible, "断言失败：元素不可见"

    def assert_60is_clickable(self, locator: Tuple[str, str], wait_time_out: Optional[int] = None, **kwargs):
        """ 断言：元素可点击 """
        is_clickable = self.web_driver_wait_until(
            ec.element_to_be_clickable(locator),
            wait_time_out=wait_time_out or self.wait_time_out
        )
        assert is_clickable, "断言失败：元素不可点击"

    def assert_61is_located(self, locator: Tuple[str, str], wait_time_out: Optional[int] = None, **kwargs):
        """ 断言：元素被定位到 """
        is_located = self.web_driver_wait_until(
            ec.presence_of_element_located(locator),
            wait_time_out=wait_time_out or self.wait_time_out
        )
        assert is_located, "断言失败：元素未被定位到"

    def get_screenshot(self, image_path: str, **kwargs):
        """ 获取屏幕截图，保存为文件 """
        try:
            if not os.path.exists(image_path):
                os.makedirs(image_path)
            screenshot_filename = os.path.join(image_path, time.strftime("%Y-%m-%d %H_%M_%S") + ".png")
            self.driver.get_screenshot_as_file(screenshot_filename)
        except Exception as e:
            raise Exception(f"截图保存失败：{str(e)}") from e

    def get_screenshot_as_base64(self, **kwargs):
        """ 获取屏幕截图，保存的是base64的编码格式，在HTML界面输出截图的时候，会用到 """
        return self.driver.get_screenshot_as_base64()

    def get_screenshot_as_file(self, filename: str, **kwargs):
        """ 获取屏幕截图，保存为二进制数据 """
        return self.driver.get_screenshot_as_file(filename)

    def get_screenshot_as_png(self, **kwargs):
        """ 获取屏幕截图, 保存为png格式 """
        return self.driver.get_screenshot_as_png()


async def get_app_client(*args, **kwargs):
    """ 实例化driver（异步执行，优化超时处理） """
    max_workers = min(50, os.cpu_count() * 5)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        try:
            bound_func = partial(AppClient, **kwargs)
            return await asyncio.wait_for(
                asyncio.get_running_loop().run_in_executor(executor, bound_func), timeout=600
            )
        except asyncio.TimeoutError:
            raise TimeoutError("AppClient 实例化超时（超过10分钟）")
        except Exception as e:
            executor.shutdown(wait=True)  # 强制终止超时任务
            raise Exception(f"AppClient 实例化失败：{str(e)}") from e


if __name__ == '__main__':
    pass
