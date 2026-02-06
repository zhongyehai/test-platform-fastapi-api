import asyncio
import base64
import json
import os
import platform
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from functools import partial
from typing import Optional, Union
from unittest.case import SkipTest

from playwright.async_api import (
    async_playwright,
    Playwright,
    Dialog,
    expect,
    TimeoutError as PlaywrightTimeoutError,
    Error as PlaywrightError
)

from utils.client.test_runner.client.base_client import BaseSession, BaseClient
from utils.client.test_runner.exceptions import RunTimeException  # TimeoutException,
from utils.util.file_util import FileUtil
from ..utils import get_dict_data


class UIClientSession(BaseSession):
    """ 实例化页面执行器上下文 """

    async def async_do_action(self, client, name=None, case_id=None, variables_mapping={}, **kwargs):
        """ 执行操作 """
        kwargs.update(dict(client=client, name=name, case_id=case_id, variables_mapping=variables_mapping))
        if client.__class__.__name__.startswith('App'):  # appium，防止执行步骤时阻塞线程
            max_workers = min(50, os.cpu_count() * 5)
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                try:
                    bound_func = partial(self.do_appium_action, *(), **kwargs)
                    return await asyncio.get_running_loop().run_in_executor(executor, bound_func)
                except Exception as e:
                    raise
        else:
            try:
                return await self.do_playwright_action(**kwargs)
            except Exception as e:
                raise

    @classmethod
    async def save_screenshot_by_playwright(cls, client, save_path):
        """ 保存 Playwright 截图（需要 await） """
        base64_screenshot = await client.get_screenshot_as_base64()
        FileUtil.save_file(save_path, base64_screenshot)

    async def do_playwright_action(self, client, name=None, case_id=None, variables_mapping={}, **kwargs):
        """ 执行操作 """
        self.meta_data["name"] = name  # 记录测试名
        self.meta_data["case_id"] = case_id  # 步骤对应的用例id
        self.meta_data["variables_mapping"] = variables_mapping  # 记录发起此次请求时内存中的自定义变量
        self.meta_data["data"][0]["test_action"] = kwargs  # 记录原始的请求信息
        report_img_folder, report_step_id = kwargs.pop("report_img_folder"), kwargs.pop("report_step_id")

        # 执行前截图
        before_page_folder = os.path.join(report_img_folder, f'{report_step_id}_before_page.txt')
        base64_screenshot = await client.get_screenshot_as_base64()
        FileUtil.save_file(before_page_folder, base64_screenshot)

        # 执行测试步骤
        start_at = datetime.now()
        result = await self._do_playwright_action(client, **kwargs)  # 执行核心步骤
        end_at = datetime.now()

        # 执行后截图
        after_page_folder = os.path.join(report_img_folder, f'{report_step_id}_after_page.txt')
        base64_screenshot = await client.get_screenshot_as_base64()
        FileUtil.save_file(after_page_folder, base64_screenshot)

        # 记录消耗的时间
        self.meta_data["stat"] = {
            "elapsed_ms": round((end_at - start_at).total_seconds() * 1000, 3),  # 执行步骤耗时, 秒转毫秒
            "request_at": start_at.strftime("%Y-%m-%d %H:%M:%S.%f"),
            "response_at": end_at.strftime("%Y-%m-%d %H:%M:%S.%f"),
        }

        return result

    @classmethod
    async def _do_playwright_action(cls, client, **kwargs):
        """ 执行操作 """
        try:
            action_name = kwargs.get('action')
            action_func = getattr(client, action_name)

            if 'open' in action_name:  # 打开页面
                return await action_func(kwargs.get('element'))

            # 不需要定位元素、不需要输入数据的方法，直接执行
            elif any(key in action_name for key in ['close', 'quit', 'get_screenshot_as_base64']):
                return await action_func()
            else:
                wait_time_out = kwargs.get('wait_time_out')
                run_action = action_func(
                    locator=(kwargs.get('by_type'), kwargs.get('element')),
                    text=kwargs.get('text'),
                    screen=kwargs.get('screen'),
                    wait_time_out=wait_time_out * 1000  # playwright 单位是毫秒
                )
                return await run_action

        except PlaywrightTimeoutError as e:
            raise RunTimeException(f'Playwright执行超时：{str(e)}\n'
                                   f'解决方案：1. 延长对应操作的 timeout 参数；2. 检查网络是否稳定；3. 确认元素选择器是否正确')
        except PlaywrightError as e:
            raise RunTimeException(f'Playwright等待元素超时：{str(e)}\n'
                                   f'解决方案：1. 检查元素选择器是否有效；2. 确认页面是否正常加载；3. 避免操作未渲染完成的元素')
        except Exception as e:
            if isinstance(e, SkipTest):
                raise
            else:
                raise RunTimeException(f'未知运行时异常，请检查:\n{traceback.print_exc()}')


class UIClient(BaseClient):
    """ Playwright 客户端 """

    def __init__(self, browser_name: str = "chromium"):
        self.browser_name = browser_name
        self.dialog: Optional[Dialog] = None
        self.playwright: Optional[Playwright] = None
        self.browser_type = None
        self.browser = None
        self.context = None
        self.page = None

    async def init_playwright(self):
        """ 初始化Playwright """
        self.playwright = await async_playwright().start()  # 启动playwright
        if self.browser_name.lower() in ["chromium", "chrome"]:
            self.browser_type = self.playwright.chromium
        elif self.browser_name.lower() == "firefox":
            self.browser_type = self.playwright.firefox
        elif self.browser_name.lower() == "webkit":
            self.browser_type = self.playwright.webkit
        else:
            raise ValueError(f"不支持的浏览器类型：{self.browser_name}")

        # 启动浏览器
        launch_args = [
            "--no-sandbox",  # 关闭沙箱，解决服务器权限不足问题
            "--disable-setuid-sandbox",  # root用户运行时必加
            "--disable-dev-shm-usage",  # 解决/dev/shm空间不足问题
            "--disable-gpu",  # 服务器无GPU，加这个避免警告/报错
            "--no-zygote",  # 服务器环境优化，减少资源占用
        ]
        # 设置窗口最大化
        if platform.platform().startswith("mac"):
            launch_args.append("--kiosk")
        elif platform.system() == "Windows":
            launch_args.append("--start-maximized")

        self.browser = await self.browser_type.launch(
            headless=True if platform.platform().startswith("Linux") else False,
            slow_mo=500,
            args=launch_args
        )
        context_kwargs = {
            "no_viewport": True,  # 关键：取消视口限制，让页面自适应尺寸
        }
        if platform.system() == "Linux":
            context_kwargs["viewport"] = {"width": 1920, "height": 1080}

        # 创建上下文和页面
        self.context = await self.browser.new_context(**context_kwargs)
        self.page = await self.context.new_page()

        # 页面创建后，再次确认视口（防止部分网站强制修改窗口）
        # await self.page.set_viewport_size({"width": 1920, "height": 1080})


    async def close_all(self):
        """ 关闭所有资源 """
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            print(f"浏览器关闭完成")
        except Exception as error:
            print(f"浏览器关闭报错: {error}")

    async def find_element(self, locator: tuple, index=None, timeout=10000):
        """ 查找元素 """
        """
            - page.get_by_role() - 通过显式和隐式的无障碍访问属性来定位元素。
            - page.get_by_text() - 通过文本内容来定位元素。
            - page.get_by_label() - 通过关联标签的文本来定位表单控件。
            - page.get_by_placeholder() - 通过占位符文本来定位输入框。
            - page.get_by_alt_text() - 通过替代文本来定位元素，通常是图片。
            - page.get_by_title() - 通过title属性来定位元素。
            - page.get_by_test_id() - 通过data-testid属性来定位元素（也可以配置使用其他属性）。
            - page.locator() - 通过CSS / XPATH定位元素。

            index: 当元素为多个时，取索引第几个
        """
        locate_by, locate_element = locator
        if locate_by == "role":
            role_name = locate_element.split(",")[0].strip()
            name_param = locate_element.split("name=")[-1] if 'name=' in locate_element else None
            page_element = self.page.get_by_role(role_name, name=name_param) if name_param else self.page.get_by_role(
                role_name)
        else:
            # 支持playwright的get_by_*系列方法
            if hasattr(self.page, f"get_by_{locate_by}"):
                page_element = getattr(self.page, f"get_by_{locate_by}")(locate_element)
            else:
                # 默认为locator（CSS/XPATH）
                page_element = self.page.locator(locate_element)

        await page_element.wait_for(timeout=float(timeout or 10000))  # 等待元素
        return page_element if index is None else page_element.nth(index)

    #################################### 点击相关事件 ####################################
    async def action_01_01_click_exist(self, locator: tuple, wait_time_out: int = None, *args, **kwargs):
        """ 【点击】元素存在就点击 """
        try:
            element = await self.find_element(locator, timeout=wait_time_out)  # 查找元素
        except:
            raise SkipTest(f"【元素存在就点击】触发跳过")
        if element:
            await element.click()

    async def action_01_02_click(self, locator: tuple, wait_time_out: int = None, *args, **kwargs):
        """ 【点击】直接点击元素 """
        element = await self.find_element(locator, timeout=wait_time_out)  # 查找元素
        await element.click()

    async def action_01_03_click_alert_accept(self, *args, **kwargs):
        """ 【点击】点击alert/confirm/prompt确定按钮 """

        def handle_dialog(dialog: Dialog):
            self.dialog = dialog
            dialog.accept()  # 点击确定

        self.page.on("dialog", handle_dialog)
        self.page.remove_listener("dialog", handle_dialog)

    async def action_01_04_click_alert_dismiss(self, *args, **kwargs):
        """ 【点击】点击alert/confirm/prompt取消按钮 """

        def handle_dialog(dialog: Dialog):
            self.dialog = dialog
            dialog.dismiss()  # 点击取消

        self.page.on("dialog", handle_dialog)
        self.page.remove_listener("dialog", handle_dialog)

    async def action_01_05_click_position(self, locator: tuple, *args, **kwargs):
        """ 【点击】点击坐标，locator = ("bounds","[[918,1079], [1080,1205]]")"""
        bounds = json.loads(locator[1])  # [[918,1079], [1080,1205]]
        bounds1, bounds2, = bounds[0], bounds[1]  # [918,1079], [1080,1205]
        x1, y1, x2, y2 = bounds1[0], bounds1[1], bounds2[0], bounds2[1]
        center_x, center_y = (x1 + x2) / 2, (y1 + y2) / 2
        await self.page.mouse.move(center_x, center_y)  # 移动鼠标
        await self.page.mouse.click(center_x, center_y)  # 点击鼠标

    #################################### 输入相关事件 ####################################
    async def action_02_01_clear_and_send_keys_is_input(self, locator: tuple, text=None, index=None, *args, **kwargs):
        """ 【输入】清空后输入 """
        element = await self.find_element(locator, index)  # 查找元素
        await element.clear()  # 清空
        await element.fill(text)  # 填充

    async def action_02_02_click_and_clear_and_send_keys_is_input(self, locator: tuple, text=None, index=None, *args,
                                                                  **kwargs):
        """ 【输入】点击并清空后输入 """
        element = await self.find_element(locator, index)  # 查找元素
        await element.click()  # 点击
        await element.clear()  # 清空
        await element.fill(text)  # 填充

    async def action_02_03_send_keys_is_input(self, locator: tuple, text=None, index=None, *args, **kwargs):
        """ 【输入】追加输入 """
        element = await self.find_element(locator, index)  # 查找元素
        await element.fill(text)  # 填充

    async def action_02_04_click_and_send_keys_is_input(self, locator: tuple, text=None, index=None, *args, **kwargs):
        """ 【输入】点击并追加输入 """
        element = await self.find_element(locator, index)  # 查找元素
        await element.click()  # 点击
        await element.fill(text)  # 填充

    async def action_02_05_send_keys_by_keyboard_is_input(self, locator: tuple, text=None, index=None, *args, **kwargs):
        """ 【输入】模拟键盘输入 """
        element = await self.find_element(locator, index)  # 查找元素
        await element.press(text)  # 按键

    async def action_02_06_click_and_send_keys_by_keyboard_is_input(self, locator: tuple, text=None, index=None, *args,
                                                                    **kwargs):
        """ 【输入】点击并模拟键盘输入 """
        element = await self.find_element(locator, index)  # 查找元素
        await element.click()  # 点击
        await element.press(text)  # 按键

    async def action_02_07_click_and_clear_and_send_keys_is_input(self, locator: tuple, text=None, index=None, *args,
                                                                  **kwargs):
        """ 【输入】元素存在则清空后输入 """
        element = await self.find_element(locator, index)  # 查找元素
        if await element.count() == 0:  # 获取元素数量
            raise SkipTest(f"【元素存在则清空后输入】触发跳过")
        await element.clear()  # 清空
        await element.fill(text)  # 填充

    async def action_02_08_click_and_clear_and_send_keys_is_input(self, locator: tuple, text=None, index=None, *args,
                                                                  **kwargs):
        """ 【输入】元素存在则点击并清空后输入 """
        element = await self.find_element(locator, index)  # 查找元素
        if await element.count() == 0:  # 获取元素数量
            raise SkipTest(f"【元素存在则清空后输入】触发跳过")
        await element.click()  # 点击
        await element.clear()  # 清空
        await element.fill(text)  # 填充

    async def action_02_09_click_and_send_keys_is_input(self, locator: tuple, text=None, index=None, *args, **kwargs):
        """ 【输入】元素存在则追加输入 """
        element = await self.find_element(locator, index)  # 查找元素
        if await element.count() == 0:  # 获取元素数量
            raise SkipTest(f"【元素存在则追加输入】触发跳过")
        await element.fill(text)  # 填充

    async def action_02_10_click_and_send_keys_is_input(self, locator: tuple, text=None, index=None, *args, **kwargs):
        """ 【输入】元素存在则点击并追加输入 """
        element = await self.find_element(locator, index)  # 查找元素
        if await element.count() == 0:  # 获取元素数量
            raise SkipTest(f"【元素存在则点击并追加输入】触发跳过")
        await element.click()  # 点击
        await element.fill(text)  # 填充

    #################################### 选中相关事件 ####################################
    async def action_03_01_checkbox_check(self, locator: tuple, wait_time_out=None, *args, **kwargs):
        """ 【选中】选中复选框/单选框 """
        await self.page.check(locator[1])  # 选中

    async def action_03_01_checkbox_uncheck(self, locator: tuple, wait_time_out=None, *args, **kwargs):
        """ 【选中】取消选中复选框 """
        await self.page.uncheck(locator[1])  # 取消选中

    async def action_03_03_select_by_index_is_input(self, locator: tuple, index: int = 0, wait_time_out=None, *args,
                                                    **kwargs):
        """ 【选中】下拉框，通过索引选中 """
        await self.page.select_option(locator[1], index=index)  # 选择

    async def action_03_04_select_by_value_is_input(self, locator: tuple, value: str = '', wait_time_out=None, *args,
                                                    **kwargs):
        """ 【选中】下拉框，通过value选中 """
        await self.page.select_option(locator[1], value=value)  # 选择

    async def action_03_05_select_by_text_is_input(self, locator: tuple, text: str = '', wait_time_out=None, *args,
                                                   **kwargs):
        """ 【选中】下拉框，通过文本值选中 """
        await self.page.select_option(locator[1], label=text)  # 选择

    #################################### 滚动相关事件 ####################################
    async def action_04_01_js_scroll_top(self, *args, **kwargs):
        """ 【滚动】滚动到浏览器顶部 """
        await self.page.evaluate("window.scrollTo(0, 0)")  # 执行JS
        await self.page.wait_for_timeout(3000)  # 等待

    async def action_04_02_js_scroll_end(self, *args, **kwargs):
        """ 【滚动】滚动到浏览器底部 """
        await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")  # 执行JS
        await self.page.wait_for_timeout(3000)  # 等待

    #################################### 切换相关事件 ####################################
    async def action_05_01_switch_to_window_is_input(self, locator, index: int = 0, *args, **kwargs):
        """ 【切换-浏览器】切换到指定索引的窗口 """
        page_list = self.context.pages
        if index < len(page_list):
            target_page_by_index = page_list[index]
            await target_page_by_index.bring_to_front()  # 切换到前台

    async def action_05_02_switch_to_end_window(self, *args, **kwargs):
        """ 【切换-浏览器】切换到最后一个窗口 """
        last_page = self.context.pages[-1]
        await last_page.bring_to_front()  # 切换到前台

    async def action_05_03_switch_handle_is_input(self, window_name: str, *args, **kwargs):
        """ 【切换-浏览器】切换到窗口名对应的窗口 """
        for page in self.context.pages:
            if page.window_name == window_name:
                await page.bring_to_front()  # 切换到前台
                break

    #################################### 窗口缩放相关事件（全改造） ####################################
    async def action_06_01_set_window_percentage_is_input(self, text: str = '0.5', *args, **kwargs):
        """ 【缩放】窗口缩放为指定比例 """
        return await self.page.set_viewport_scale(float(text))  # 设置缩放

    async def action_06_02_max_window(self, *args, **kwargs):
        """ 【缩放】窗口最大化 """
        window = self.page.window()
        return await window.maximize()  # 最大化

    async def action_06_03_set_window_size_is_input(self, width: float, height: float, *args, **kwargs):
        """ 【缩放】窗口缩放为指定大小值 """
        await self.context.set_viewport_size({"width": width, "height": height})  # 设置视口大小

    #################################### 获取对象相关事件 ####################################
    async def action_07_01_get_current_handle(self, *args, **kwargs):
        """ 【获取】获取当前句柄 """
        return self.page.window_handle

    async def action_07_02_get_handles(self, *args, **kwargs):
        """ 【获取】获取所有句柄 """
        return [window.window_handle for window in self.page.context.windows]

    async def action_07_03_get_name(self, *args, **kwargs):
        """ 【获取】获取浏览器名称 """
        browser_name = self.browser.type
        # 映射为与 Selenium 相近的返回值（可选，也可直接返回 browser_name）
        name_mapping = {
            "chromium": "chrome",
            "firefox": "firefox",
            "webkit": "safari"
        }
        return name_mapping.get(browser_name.lower(), browser_name)

    async def action_07_04_get_alert_text(self, *args, **kwargs):
        """ 【获取】获取alert文本 """
        dialog_text = None

        # 定义弹窗处理函数，捕获弹窗文本
        def _dialog_handler(dialog):
            nonlocal dialog_text
            dialog_text = dialog.message  # 提取弹窗文本内容
            dialog.dismiss()  # 弹窗处理（可改为 accept() 确认，根据需求调整）

        # 注册弹窗监听
        self.page.on("dialog", _dialog_handler)

        # 等待弹窗出现并捕获文本，超时则抛出异常
        try:
            await self.page.wait_for_event("dialog", timeout=5000)  # 等待事件
        except TimeoutError:
            raise AssertionError("获取失败：页面不存在 alert 弹窗")

        return dialog_text

    async def action_07_05_get_size(self, locator: tuple, *args, **kwargs):
        """ 【获取】获取元素大小 """
        element = await self.find_element(locator)  # 查找元素
        bounding_box = await element.bounding_box()  # 获取边界框
        if not bounding_box:
            raise AssertionError(f"获取失败：无法获取选择器【{locator}】对应的元素大小")
        # 返回与 Selenium 相同的字典格式：{'width': 数值, 'height': 数值}
        return {
            "width": bounding_box["width"],
            "height": bounding_box["height"]
        }

    #################################### 浏览器操作相关事件 ####################################
    async def action_08_01_open(self, url: str, *args, **kwargs):
        """ 【浏览器】打开url """
        await self.page.goto(url)  # 跳转

    async def action_08_02_close(self, *args, **kwargs):
        """ 【浏览器】关闭浏览器 """
        await self.browser.close()  # 关闭浏览器

    async def action_08_03_quit(self, *args, **kwargs):
        """ 【浏览器】关闭窗口 """
        await self.page.close()  # 关闭页面

    #################################### 上传相关事件 ####################################
    async def action_09_01_upload_one_file_is_upload(self, locator, file_path, *args, **kwargs):
        """ 【上传】上传单个文件 """
        locator_obj = self.page.locator(locator[1])  # 修正：locator[1]是定位表达式
        await locator_obj.set_input_files(file_path)  # 设置上传文件

    async def action_09_02_upload_multi_file_is_upload(self, locator, file_path_list: list[str], *args, **kwargs):
        """ 【上传】上传多个文件 """
        locator_obj = self.page.locator(locator[1])  # 修正：locator[1]是定位表达式
        await locator_obj.set_input_files(file_path_list)  # 设置上传文件

    async def action_09_03_upload_file_clear(self, locator, *args, **kwargs):
        """ 【上传】清空已选择的上传文件 """
        locator_obj = self.page.locator(locator[1])  # 修正：locator[1]是定位表达式
        await locator_obj.set_input_files([])  # 清空上传文件

    #################################### JS相关事件 ####################################
    async def action_10_01_js_execute_is_input(self, js: str, *args, **kwargs):
        """ 【JS】执行js """
        await self.page.evaluate(js)  # 执行JS

    async def action_10_02_js_focus_element(self, locator: tuple, text: str = '', wait_time_out=None, *args, **kwargs):
        """ 【JS】聚焦元素 """
        locator_obj = await self.find_element(locator, timeout=wait_time_out)  # 查找元素
        await locator_obj.scroll_into_view_if_needed()  # 滚动

    async def action_10_02_js_click(self, locator: tuple, text: str = '', wait_time_out=None, *args, **kwargs):
        """ 【JS】点击元素 """
        locator_obj = await self.find_element(locator, timeout=wait_time_out)  # 查找元素
        # 执行 JS 点击，locator.evaluate() 直接传入元素到 JS 中
        await locator_obj.evaluate("element => element.click();")  # 执行JS

    async def action_10_03_add_cookie_by_dict_is_input(self, locator: tuple, cookie, *args, **kwargs):
        """ 【JS】以字典形式添加cookie """
        cookie_dict = get_dict_data(cookie)
        playwright_cookies = []
        for key, value in cookie_dict.items():
            playwright_cookies.append({
                "name": key,
                "value": str(value),  # 确保 value 为字符串格式
                "domain": self.page.url.split("//")[-1].split("/")[0],  # 自动获取当前域名
                "path": "/"
            })
        # Playwright 上下文级别添加 Cookie（专属 API，比 JS 更稳定）
        await self.context.add_cookies(playwright_cookies)  # 添加cookie

    async def action_10_04_delete_all_cookie(self, *args, **kwargs):
        """ 【JS】删除cookie中的所有数据 """
        await self.context.clear_cookies()  # 清空cookie

    async def action_10_05_set_session_storage_value_by_dict_is_input(self, locator: tuple, data: dict, *args,
                                                                      **kwargs):
        """ 【JS】以字典的形式在sessionStorage中设置数据 """
        data_dict = get_dict_data(data)
        # 遍历字典，执行 JS 设置 sessionStorage
        for key, value in data_dict.items():
            # 推荐使用参数传递（避免字符串拼接的引号转义问题）
            await self.page.evaluate(
                "([key, value]) => window.sessionStorage.setItem(key, value);",
                [str(key), str(value)]
            )  # 执行JS

    async def action_10_06_clear_session_storage_value(self, *args, **kwargs):
        """ 【JS】清空sessionStorage中的所有数据 """
        return await self.page.evaluate("window.sessionStorage.clear();")  # 执行JS

    async def action_10_07_set_local_storage_value_by_dict_is_input(self, locator: tuple, data: dict, *args, **kwargs):
        """ 【JS】以字典的形式在localStorage中设置数据 """
        data_dict = get_dict_data(data)
        # 遍历字典，执行 JS 设置 localStorage（参数传递，避免转义问题）
        for key, value in data_dict.items():
            await self.page.evaluate(
                "(key, value) => window.localStorage.setItem(key, value);",
                [str(key), str(value)]
            )  # 执行JS

    async def action_10_08_clear_local_storage_value(self, *args, **kwargs):
        """ 【JS】清空localStorage中的所有数据 """
        await self.page.evaluate("window.localStorage.clear();")  # 执行JS

    #################################### 辅助相关事件 ####################################
    async def action_11_01_sleep_is_input(self, time_seconds: Union[int, float, str], *args, **kwargs):
        """ 【辅助】等待指定时间 """
        sleep_seconds = float(time_seconds) if isinstance(time_seconds, str) else time_seconds
        await asyncio.sleep(sleep_seconds)  # 等待

    async def action_11_02_nothing_to_do(self, *args, **kwargs):
        """ 【辅助】不操作元素 """
        return

    #################################### 数据提取相关事件 ####################################
    async def extract_08_title(self, *args, **kwargs):
        """ 获取title """
        return await self.page.title()  # 获取标题

    async def extract_09_text(self, locator: tuple, *args, **kwargs):
        """ 获取文本 """
        element = await self.find_element(locator)  # 查找元素
        text = await element.inner_text()  # 获取文本
        return text.strip()

    async def extract_09_value(self, locator: tuple, wait_time_out=None, *args, **kwargs):
        """ 获取value值 """
        element = await self.find_element(locator, timeout=wait_time_out)  # 查找元素
        return await element.input_value()  # 获取输入值

    async def extract_09_cookie(self, *args, **kwargs):
        """ 获取cookie值 """
        return await self.page.context.cookies()  # 获取cookie

    async def extract_09_session_storage(self, *args, **kwargs):
        """ 获取sessionStorage值 """
        return await self.page.evaluate("() => { return JSON.parse(JSON.stringify(sessionStorage)); }")  # 执行JS

    async def extract_09_local_storage(self, *args, **kwargs):
        """ 获取localStorage值 """
        return await self.page.evaluate("() => { return JSON.parse(JSON.stringify(localStorage)); }")  # 执行JS

    async def extract_10_attribute_is_input(self, locator: tuple, name: str, wait_time_out=None, *args, **kwargs):
        """ 获取指定属性 """
        element = await self.find_element(locator, timeout=wait_time_out)  # 查找元素
        return await element.get_attribute(name)  # 获取属性

    #################################### 断言相关方法 ####################################
    async def assert_50str_in_value(self, locator: tuple, value: str, *args, **kwargs):
        """ 元素value值包含 """
        expect_value = await self.extract_09_value(locator)  # 提取值
        assert value in expect_value, {'expect_value': expect_value}

    async def assert_51_element_value_equal_to(self, locator: tuple, content, *args, **kwargs):
        """ 元素value值等于 """
        expect_value = await self.extract_09_value(locator)  # 提取值
        assert expect_value == content, f'实际结果：{expect_value}'

    async def assert_52_element_value_larger_than(self, locator: tuple, content, *args, **kwargs):
        """ 元素value值大于 """
        expect_value = await self.extract_09_value(locator)  # 提取值
        assert float(expect_value) > content, {'expect_value': expect_value}

    async def assert_53_element_value_smaller_than(self, locator: tuple, content, *args, **kwargs):
        """ 元素value值小于 """
        expect_value = await self.extract_09_value(locator)  # 提取值
        assert float(expect_value) < content, {'expect_value': expect_value}

    async def assert_54is_selected_be(self, locator: tuple, *args, **kwargs):
        """ 元素被选中 """
        element = await self.find_element(locator)  # 查找元素
        is_checked = await element.is_checked()  # 判断是否选中
        assert is_checked, {'msg': '元素未被选中'}

    async def assert_55is_not_selected_be(self, locator: tuple, *args, **kwargs):
        """ 元素未被选中 """
        element = await self.find_element(locator)  # 查找元素
        is_checked = await element.is_checked()  # 判断是否选中
        assert is_checked is False, {'msg': '元素已被选中'}

    async def assert_56_element_txt_equal_to(self, locator: tuple, content, *args, **kwargs):
        """ 元素txt值等于 """
        expect_value = await self.extract_09_text(locator)  # 提取文本
        assert expect_value == content, f'实际结果：{expect_value}'

    async def assert_56_element_txt_larger_than(self, locator: tuple, content, *args, **kwargs):
        """ 元素txt值大于 """
        expect_value = await self.extract_09_text(locator)  # 提取文本
        assert float(expect_value) > content, {'expect_value': expect_value}

    async def assert_56_element_txt_smaller_than(self, locator: tuple, content, *args, **kwargs):
        """ 元素txt值小于 """
        expect_value = await self.extract_09_text(locator)  # 提取文本
        assert float(expect_value) < content, {'expect_value': expect_value}

    async def assert_57text_in_element(self, locator: tuple, text: str, *args, **kwargs):
        """ 元素txt值包含 """
        expect_value = await self.extract_09_text(locator)  # 提取文本
        assert text in expect_value, {'expect_value': expect_value}

    async def assert_58is_visibility(self, locator: tuple, *args, **kwargs):
        """ 元素可见 """
        element = await self.find_element(locator)  # 查找元素
        await expect(element).to_be_visible()  # 断言

    async def assert_60is_clickable(self, locator: tuple, wait_time_out=None, *args, **kwargs):
        """ 元素可点击 """
        element = await self.find_element(locator, timeout=wait_time_out)  # 查找元素
        await expect(element).to_be_clickable()  # 断言

    async def assert_61is_located(self, locator: tuple, wait_time_out=None, *args, **kwargs):
        """ 元素被定为到 """
        element = await self.find_element(locator, timeout=wait_time_out)  # 查找元素
        await expect(element).to_be_attached()  # 断言

    async def assert_62is_title(self, text: str, *args, **kwargs):
        """ 页面title等于 """
        expect_value = await self.extract_08_title()  # 提取标题
        assert text == expect_value, {'expect_value': expect_value}

    async def assert_63is_title_contains(self, text: str, *args, **kwargs):
        """ 页面title包含 """
        expect_value = await self.extract_08_title()  # 提取标题
        assert text in expect_value, {'expect_value': expect_value}

    async def assert_64is_alert_present(self, wait_time_out=None, *args, **kwargs):
        """ 页面有alert """

        def _dialog_handler(dialog):
            dialog.dismiss()  # 可改为 dialog.accept() 确认弹窗，根据需求调整

        self.page.on("dialog", _dialog_handler)
        # 验证 dialog 存在（Playwright 无直接断言，通过尝试获取来验证）
        try:
            await self.page.wait_for_event("dialog", timeout=5000)  # 等待事件
        except TimeoutError:
            raise AssertionError("断言失败：页面不存在 alert 弹窗")

    async def assert_65is_iframe(self, locator: tuple, wait_time_out=None, *args, **kwargs):
        """ 元素为iframe """
        iframe_locator = await self.find_element(locator, timeout=wait_time_out)  # 查找元素
        await expect(iframe_locator).to_be_attached()  # 断言
        # 切换进入 iframe
        frame_locator = self.page.frame_locator(locator[1])  # 修正：locator[1]是定位表达式
        assert frame_locator is not None, "断言失败：元素不是有效的 iframe"

    #################################### 截图相关方法 ####################################
    async def get_screenshot(self, image_path: str, *args, **kwargs):
        """ 保存截图到文件 """
        import time  # 局部导入，避免同步模块全局影响
        screenshot_filename = os.path.join(image_path, time.strftime("%Y-%m-%d %H_%M_%S") + ".png")
        await self.page.screenshot(path=screenshot_filename, full_page=True)  # 截图

    async def get_screenshot_as_base64(self, *args, **kwargs):
        """ 获取base64格式截图 """
        screenshot_bytes = await self.page.screenshot(type="png", full_page=True)
        if isinstance(screenshot_bytes, bytes):
            return base64.b64encode(screenshot_bytes).decode("utf-8")
        else:
            return ""

    async def get_screenshot_as_file(self, filename: str, *args, **kwargs):
        """ 保存截图为文件 """
        return await self.page.screenshot(path=filename, full_page=True)  # 截图

    async def get_screenshot_as_png(self, *args, **kwargs):
        """ 获取png格式截图字节流 """
        return await self.page.screenshot(type="png", full_page=True)  # 截图


async def get_ui_client(browser_name, *args, **kwargs):
    """ 获取UIClient实例 """
    try:
        ui_client = UIClient(browser_name=browser_name)
        await ui_client.init_playwright()  # 初始化playwright
        return ui_client
    except Exception as e:
        raise
