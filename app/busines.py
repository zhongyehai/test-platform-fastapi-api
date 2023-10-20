import asyncio
import os

from app.api_test.model_factory import ApiProject, ApiProjectEnv, ApiReport
from app.ui_test.model_factory import WebUiProject, WebUiProjectEnv, WebUiReport
from app.app_test.model_factory import AppUiProject, AppUiProjectEnv, AppUiReport
from app.config.model_factory import RunEnv, Config
from config import job_server_host, tortoise_orm_conf
from utils.make_data.make_xmind import get_xmind_first_sheet_data
from utils.util.file_util import TEMP_FILE_ADDRESS
from utils.util import request as async_requests


class ProjectBusiness:
    """ 项目管理业务 """

    @classmethod
    async def add_project(cls, project_data, request, project_model, env_model, suite_model):
        project = await project_model.model_create(project_data, request.state.user)
        # 新增服务的时候，一并把运行环境、用例集设置齐全
        await env_model.create_env(RunEnv, project_model, project.id)
        await suite_model.create_suite_by_project(project.id)
        return project

    @classmethod
    async def delete_project(cls, project, module_model, case_suit_model, task_model):
        """ 删除服务及服务下的模块、用例集、任务 """
        await task_model.filter(project_id=project.id).delete()  # 删除任务
        await case_suit_model.filter(project_id=project.id).delete()  # 删除用例集
        await module_model.filter(project_id=project.id).delete()  # 删除模块
        await project.model_delete()  # 删除服务

    @classmethod
    async def chang_env(cls, project_env, new_env_data, user, filed_list):
        # 更新服务的环境
        await project_env.model_update(new_env_data, user)

        # 把环境的头部信息、变量的key一并同步到其他环境
        project_env_list = await project_env.__class__.filter(
            project_id=project_env.project_id, id__not=project_env.env_id).values("env_id")
        env_id_list = [env["env_id"] for env in project_env_list]
        await project_env.__class__.synchronization(new_env_data, env_id_list, filed_list)


class ProjectEnvBusiness:
    """ 项目环境管理业务 """

    @classmethod
    def put(cls, form, env_model, filed_list):
        form.env_data.update(form.data)

        # 更新环境的时候，把环境的头部信息、变量的key一并同步到其他环境
        env_list = [
            env.env_id for env in env_model.get_all(project_id=form.project_id.data) if
            env.env_id != form.env_data.env_id
        ]
        env_model.synchronization(form.env_data, env_list, filed_list)

    @classmethod
    async def add_env(cls, env_id):
        """ 批量给服务/项目/app添加运行环境 """
        await ApiProjectEnv.add_env(env_id, ApiProject)
        await WebUiProjectEnv.add_env(env_id, WebUiProject)
        await AppUiProjectEnv.add_env(env_id, AppUiProject)


class ElementBusiness:
    """ 元素管理业务 """

    @classmethod
    def post(cls, form, model, is_update_addr=False):
        element_list = []
        for element in form.element_list.data:
            element["project_id"] = form.project_id.data
            element["module_id"] = form.module_id.data
            element["page_id"] = form.page_id.data
            element["num"] = model.get_insert_num(page_id=form.page_id.data)
            new_element = model().create(element)
            element_list.append(new_element)
        if is_update_addr:
            form.update_page_addr()
        return element_list


class CaseSuiteBusiness:
    """ 用例集管理业务 """

    @classmethod
    async def upload_case_suite(cls, project_id, file_obj, suite_model, case_model):
        file_path = os.path.join(TEMP_FILE_ADDRESS, file_obj.filename)

        # 保存文件
        file_content = await file_obj.read()
        with open(file_path, 'wb') as f:
            f.write(file_content)

        # 读取文件内容，并创建数据
        xmind_data = get_xmind_first_sheet_data(file_path)
        return await suite_model.upload(project_id, xmind_data, case_model)


class CaseBusiness:
    """ 用例业务 """

    @classmethod
    async def copy(cls, case, case_model, step_model, user):
        # 复制用例
        old_case = dict(case)
        old_case["name"] = old_case["name"] + "_copy"
        old_case["status"] = 0
        new_case = await case_model.model_create(old_case, user)

        # 复制步骤
        old_step_list = await step_model.filter(case_id=case.id).order_by("num").all()
        for index, old_step in enumerate(old_step_list):
            step = dict(old_step)
            step["case_id"] = new_case.id
            new_step = await step_model.model_create(step, user)
            if "Api" in step_model.__name__:  # 接口自动化
                await new_step.add_quote_count()
        return new_case

    @classmethod
    async def copy_case_all_step_to_current_case(cls, form, step_model, case_model, user):
        """ 复制指定用例的步骤到当前用例下 """
        from_case, to_case, step_list = form.from_case, form.to_case, []
        case_list = await step_model.filter(case_id=from_case).order_by("num").all()

        for index, step in enumerate(case_list):
            step_dict = dict(step)
            step_dict["case_id"] = to_case
            new_step = await step_model.model_create(step_dict, user)
            step_list.append(dict(new_step))
            if "Api" in step_model.__name__:  # 如果是api的，则增加接口引用
                await step.add_quote_count()
        await case_model.merge_output(to_case, step_list)  # 合并出参
        return step_list

    @classmethod
    async def get_quote_case_from(cls, case, project_model, suite_model):
        """ 获取用例的归属 """
        suite_path_name = await suite_model.get_from_path(case.suite_id)
        suite = await suite_model.filter(id=case.suite_id).first()
        project = await project_model.filter(id=suite.project_id).first()
        return f'{project.name}/{suite_path_name}/{case.name}'


class StepBusiness:
    """ 步骤业务 """

    @classmethod
    async def add_step(cls, step_data, step_model, case_model, user):
        """ 新增步骤 """
        step = await step_model.model_create(step_data, user)
        if "Api" in step_model.__name__:  # 接口自动化
            await step.add_quote_count()
        await case_model.merge_variables(step.quote_case, step.case_id)
        await case_model.merge_output(step.case_id, [int(step.quote_case) if step.quote_case else step])  # 合并出参
        return step

    @classmethod
    async def copy(cls, step_id, case_id, step_model, case_model, user):
        """ 复制步骤，如果没有指定用例id，则默认复制到当前用例下 """
        step = await step_model.filter(id=step_id).first()
        step.name = f'{step.name}_copy'
        if case_id:
            step.case_id = case_id
        new_step = await step_model.model_create(dict(step), user)
        if "Api" in step_model.__name__:  # 接口自动化
            await new_step.add_quote_count()
        await case_model.merge_output(new_step.case_id, [new_step])  # 合并出参
        return new_step


class TaskBusiness:
    """ 任务业务 """

    @classmethod
    async def copy(cls, task, task_model, user):
        task_dict = dict(task)
        task_dict["name"], task_dict["status"] = task_dict["name"] + "_copy", 0
        return await task_model.model_create(task_dict, user)

    @classmethod
    async def enable(cls, task, task_type, user, token):
        """ 启用任务 """
        dict_task = dict(task)
        if "create_time" in dict_task: dict_task.pop("create_time")
        if "update_time" in dict_task: dict_task.pop("update_time")
        try:
            res = await async_requests.post(
                url=job_server_host,
                headers={"X-Token": token},
                json={"user_id": user.id, "task": dict_task, "task_type": task_type})
            res_json = res.json()
            if res_json.get("status") == 200:
                await task.enable()
                return {"status": 1, "data": res_json}
            else:
                return {"status": 0, "data": res_json}
        except Exception as error:
            return {"status": 0, "data": str(error)}

    @classmethod
    async def disable(cls, task, task_type, token):
        """ 禁用任务 """
        try:
            res = await async_requests.delete(
                url=job_server_host,
                headers={"X-Token": token},
                json={"task_code": f'{task_type}_{task.id}'}
            )
            res_json = res.json()
            if res_json.get("status") == 200:
                await task.disable()
                return {"status": 1, "data": res_json}
            else:
                return {"status": 0, "data": res_json}
        except Exception as error:
            return {"status": 0, "data": str(error)}


class RunCaseBusiness:
    """ 运行用例 """

    @classmethod
    async def has_worker_to_run_test(cls, request):
        """ 判断是否有空闲的worker执行测试 """
        api_running_count = await ApiReport.get_last_10_minute_running_count()
        ui_running_count = await WebUiReport.get_last_10_minute_running_count()
        app_running_count = await AppUiReport.get_last_10_minute_running_count()
        return (api_running_count + ui_running_count + app_running_count) <= (request.app.conf.main_server_workers - 2)

    @classmethod
    async def run(
            cls, is_async, project_id, report_name, task_type, report_model, case_id_list, run_type, runner,
            batch_id=None, env_code=None, browser=None, report_id=None, trigger_type="page", task_dict={},
            temp_variables=None, appium_config={}, extend_data={}, create_user=None, trigger_id=None,  # 保存触发源的id，方便触发重跑
    ):
        """ 运行用例/任务 """
        env = await RunEnv.get_data_byid_or_code(env_code=env_code)
        summary = report_model.get_summary_template()
        summary["env"]["code"], summary["env"]["name"] = env.code, env.name
        report = report_id or await report_model.get_new_report(
            name=report_name,
            run_type=task_type,
            create_user=create_user,
            project_id=project_id,
            env=env.code,
            trigger_type=trigger_type,
            temp_variables=temp_variables or {},
            batch_id=batch_id,
            run_id=trigger_id or case_id_list,
            is_async=is_async,
            summary=summary
        )

        asyncio.create_task(runner(
            project_id=project_id,
            report=report,
            run_name=report.name,
            case_id_list=case_id_list,
            is_async=is_async,
            env_code=env.code,
            env_name=env.name,
            browser=browser,
            task_dict=task_dict,
            temp_variables=temp_variables,
            trigger_type=trigger_type,
            run_type=run_type,
            extend=extend_data,
            appium_config=appium_config
        ).parse_and_run())

        return report.id

    @classmethod
    async def get_appium_config(cls, project_id, server, phone, no_reset=False):
        """ 获取appium配置 """
        project = await AppUiProject.filter(id=project_id).first()  # app配置
        appium_new_command_timeout = await Config.get_appium_new_command_timeout() or 120
        appium_config = {
            "host": server.ip,
            "port": server.port,
            "newCommandTimeout": int(appium_new_command_timeout),  # 两条appium命令间的最长时间间隔，若超过这个时间，appium会自动结束并退出app，单位为秒
            "noReset": no_reset,  # 控制APP记录的信息是否不重置
            # "unicodeKeyboard": True,  # 使用 appium-ime 输入法
            # "resetKeyboard": True,  # 表示在测试结束后切回系统输入法

            # 设备参数
            "platformName": phone.os,
            "platformVersion": phone.os_version,
            "deviceName": phone.device_id,

            # 用于后续自动化测试中的参数
            "server_id": server.id,  # 用于判断跳过条件
            "phone_id": phone.id,  # 用于判断跳过条件
            "device": phone.to_format_dict()  # 用于插入到公共变量
        }
        if phone.os == "Android":  # 安卓参数
            appium_config["automationName"] = "UIAutomator2"
            appium_config["appPackage"] = project.app_package
            appium_config["appActivity"] = project.app_activity
        else:  # IOS参数
            appium_config["automationName"] = "XCUITest"
            appium_config["udid"] = phone.device_id  # 设备唯一识别号(可以使用Itunes查看UDID, 点击左上角手机图标 - 点击序列号直到出现UDID为止)
            appium_config["xcodeOrgId"] = ""  # 开发者账号id，可在xcode的账号管理中查看
            appium_config["xcodeSigningId"] = "iPhone Developer"

        return appium_config
