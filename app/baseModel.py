import datetime
import time
from dateutil.relativedelta import relativedelta

from tortoise import Tortoise, fields, models
from tortoise.contrib.pydantic import pydantic_model_creator  # 统一归口，都从此处引用 pydantic_model_creator

from app.enums import DataStatusEnum, CaseStatusEnum, ApiCaseSuiteTypeEnum, ReceiveTypeEnum, TriggerTypeEnum, \
    SendReportTypeEnum
from config import api_suite_list, ui_suite_list, main_server_host
from utils.parse.parse import parse_list_to_dict, update_dict_to_list, parse_dict_to_list
from utils.util.json_util import JsonUtil


class BaseModel(models.Model, JsonUtil):
    id = fields.IntField(pk=True)
    create_time = fields.DatetimeField(auto_now_add=True, description="创建时间")
    update_time = fields.DatetimeField(auto_now=True, description="最后修改时间")
    create_user = fields.IntField(unll=True, default=1, description="创建人")
    update_user = fields.IntField(unll=True, default=1, description="最后修改人")

    class Meta:
        abstract = True  # 不生成表

    @classmethod
    async def model_create(cls, data_dict: dict, user=None, *args, **kwargs):
        """ 创建数据
         1、如果有id字段，自动去除
         2、如果模型里面有num字段，自动获取最大num数值
         3、自动加上user_id
         """
        if "id" in data_dict: data_dict.pop("id")
        if "num" in cls._meta.fields: data_dict["num"] = await cls.get_insert_num()
        if user: data_dict["create_user"] = data_dict["update_user"] = user.id
        return await cls.create(**data_dict)

    async def model_update(self, data: dict, user=None, *args, **kwargs):
        """ 根据id更新数据 """
        if "num" in data: data.pop("num")
        if user: data["update_user"] = user.id
        if "id" in data: data.pop("id")
        return await self.__class__.filter(id=self.id).update(**data)

    async def model_delete(self):
        """ 删除数据 """
        await self.__class__.filter(id=self.id).delete()

    @classmethod
    async def batch_delete(cls, **kwargs):
        await cls.filter(**kwargs).delete()

    @classmethod
    async def batch_insert(cls, data_list, user, **kwargs):
        """ 批量插入 """
        await cls.bulk_create([cls(create_user=user.id, update_user=user.id, **data) for data in data_list])

    async def enable(self):
        """ 启用数据 """
        await self.__class__.filter(id=self.id).update(status=DataStatusEnum.ENABLE)

    async def disable(self):
        """ 禁用数据 """
        await self.__class__.filter(id=self.id).update(status=DataStatusEnum.DISABLE)

    async def copy(self):
        """ 复制对象数据并插入到数据库 """
        data = dict(self)
        data["name"] = data.get("name", "") + "_copy"
        if "id" in data: data.pop("id")
        return await self.__class__.model_create(data)

    def to_format_dict(self):
        """ 转字典 """
        data = dict(self)
        data.pop("create_time")
        data.pop("update_time")
        return data

    @classmethod
    async def execute_sql(cls, sql):
        """ 执行原生SQL """
        db = Tortoise.get_connection("default")
        result = await db.execute_query_dict(sql)  # [{'methods': 'POST', 'totle': 3}]
        return result

    @classmethod
    async def execute_sql_to_dict(cls, sql):
        """ 执行原生SQL """
        res = await cls.execute_sql(sql)
        result = {}
        for item in res:
            for key, value in item.items():
                result[key] = value
        return result

    def is_enable(self):
        """ 判断数据是否为启用状态 """
        return self.status == 1

    def is_disable(self):
        """ 判断数据是否为禁用状态 """
        return self.status == 0

    @classmethod
    def filed_max_length(cls, filed):
        """ 获取字段设置的长度 """
        return cls._meta.fields_map[filed].max_length

    @classmethod
    def filter_not_get_filed(cls, not_get_filed: list = []):
        """ 根据设置的不查的字段，获取剩下要获取的字段，用于查列表时只查关键字段，提升性能 """
        return cls._meta.fields - set(not_get_filed)

    @classmethod
    def is_admin(cls, api_permissions: list):
        """ 管理员权限 """
        return 'admin' in api_permissions

    @classmethod
    def is_not_admin(cls, api_permissions: list):
        """ 非管理员权限 """
        return cls.is_admin(api_permissions) is False

    @classmethod
    async def get_from_path(cls, data_id):
        """ 获取模块/用例集的归属 """
        from_name = []

        async def get_from(m_id):
            parent = await cls.filter(id=m_id).first()
            from_name.insert(0, parent.name)

            if parent.parent:
                await get_from(parent.parent)

        await get_from(data_id)
        return '/'.join(from_name)

    @classmethod
    def has_api_permissions(cls, api_permissions, url_path):
        """ 判断用户是否有权限访问接口 """
        return cls.is_admin(api_permissions) or (url_path in api_permissions)

    def is_create_user(self, user_id: int):
        """ 判断当前传进来的id为数据创建者 """
        return self.create_user == user_id

    @classmethod
    async def change_sort(cls, id_list, page_num, page_size):
        """ 批量修改排序 """
        for index, data_id in enumerate(id_list):
            query = cls.filter(id=data_id)
            if await query.first():
                await query.update(num=(page_num - 1) * page_size + index)

    @classmethod
    async def get_max_num(cls, **kwargs):
        """ 返回 model 表中**kwargs筛选条件下的已存在编号num的最大值 """
        max_num_data = await cls.filter(**kwargs).order_by('-num').first()
        return max_num_data.num if max_num_data and max_num_data.num else 0

    @classmethod
    async def get_insert_num(cls, **kwargs):
        """ 返回 model 表中**kwargs筛选条件下的已存在编号num的最大值 + 1 """
        return await cls.get_max_num(**kwargs) + 1


class BaseProject(BaseModel):
    """ 服务基类表 """

    name = fields.CharField(255, description="服务名称")
    manager = fields.IntField(description="服务的管理员id")
    script_list = fields.JSONField(default=[], description="引用的脚本文件")
    num = fields.IntField(null=True, description="当前服务的序号")
    business_id = fields.IntField(index=True, description="所属业务线")

    class Meta:
        abstract = True  # 不生成表

    def is_manager_id(self, user_id: int):
        """ 判断当前用户为当前数据的负责人 """
        return self.manager == user_id

    def is_can_delete(self, user_id: int, user_permissions: list):
        """
        判断是否有权限删除，
        可删除条件（或）：
        1.当前用户为系统管理员
        2.当前用户为当前数据的创建者
        3.当前用户为当前要删除服务的负责人
        """
        return self.is_manager_id(user_id) or self.is_admin(user_permissions) or self.is_create_user(user_id)


class BaseProjectEnv(BaseModel):
    """ 服务环境基类表 """

    host = fields.CharField(255, default=main_server_host, description="服务地址")
    variables = fields.JSONField(
        default=[{"key": None, "value": None, "remark": None, "data_type": None}], description="服务的公共变量")

    env_id = fields.IntField(index=True, description="对应环境id")
    project_id = fields.IntField(index=True, description="所属的服务id")

    class Meta:
        abstract = True  # 不生成表

    @classmethod
    async def insert_env(cls, project_id, env_id, user_id):
        """ 获取环境的时候，没有环境，就插入一条环境记录 """
        project_env_first = await cls.filter(project_id=project_id).first()
        if project_env_first:
            insert_env_data = project_env_first.__dict__
            insert_env_data["env_id"] = env_id
        else:
            insert_env_data = {"env_id": env_id, "project_id": project_id}
        insert_env_data["create_user"] = insert_env_data["update_user"] = user_id
        return await cls.create(**insert_env_data)

    @classmethod
    async def create_env(cls, env_model, project_model, project_id=None, env_list=None):
        """
        当环境配置更新时，自动给项目/环境增加环境信息
        如果指定了项目id，则只更新该项目的id，否则更新所有项目的id
        如果已有当前项目的信息，则用该信息创建到指定的环境
        """
        if not project_id and not env_list:
            return

        env_id_list = env_list or [env["id"] for env in await env_model.all().values("id")]

        if project_id:
            current_project_env = await cls.filter(project_id=project_id).first()
            data = current_project_env.__dict__ if current_project_env else {"project_id": project_id}
            await cls.bulk_create([cls(**data, env_id=env_id) for env_id in env_id_list])

        else:
            all_project_id = [env["id"] for env in await project_model.all().values("id")]
            for project_id in all_project_id:
                await cls.create_env(env_model, project_model, project_id, env_id_list)

    @classmethod
    async def synchronization(cls, from_env: dict, to_env_id_list: list, filed_list: list):
        """ 把当前环境同步到其他环境
        from_env: 从哪个环境
        to_env_list: 同步到哪些环境
        filed_list: 指定要同步的字段列表
        """

        # 同步数据来源解析
        from_env_dict = {filed: parse_list_to_dict(from_env[filed]) for filed in filed_list}
        to_env_list = await cls.filter(project_id=from_env["project_id"], env_id__in=to_env_id_list).all()

        # 同步至指定环境
        for to_env in to_env_list:
            new_env_data = {}
            for filed in filed_list:
                from_data, to_data = from_env_dict[filed], getattr(to_env, filed)
                new_env_data[filed] = update_dict_to_list(from_data, to_data)

            await cls.filter(id=to_env.id).update(**new_env_data)  # 同步环境

    @classmethod
    async def add_env(cls, env_id, project_model):
        """ 新增运行环境时，批量给服务/项目/APP加上 """
        for project in await project_model.all():
            if not await cls.filter(project_id=project.id, env_id=env_id).first():
                await cls().create(env_id=env_id, project_id=project.id)


class BaseModule(BaseModel):
    """ 模块基类表 """

    name = fields.CharField(255, default="", description="模块名")
    num = fields.IntField(null=True, default=None, description="模块在对应服务下的序号")
    parent = fields.IntField(null=True, default=None, description="父级模块id")
    project_id = fields.IntField(index=True, description="所属的服务id")

    class Meta:
        abstract = True  # 不生成表


class BaseApi(BaseModel):
    """ 页面表 """
    name = fields.CharField(255, default="", description="接口名称")
    num = fields.IntField(null=True, default=None, description="接口序号")
    desc = fields.CharField(255, default="", description="接口描述")
    project_id = fields.IntField(null=True, index=True, default=None, description="所属的服务id")
    module_id = fields.IntField(null=True, index=True, default=None, description="所属的模块id")

    class Meta:
        abstract = True  # 不生成表


class BaseElement(BaseApi):
    """ 页面元素表 """

    by = fields.CharField(255, null=True, description="定位方式")
    element = fields.TextField(default="", null=True, description="元素值")
    wait_time_out = fields.IntField(default=5, null=True, description="等待元素出现的时间，默认5秒")
    page_id = fields.IntField(null=True, index=True, default=None, description="所属的页面id")

    class Meta:
        abstract = True  # 不生成表

    @classmethod
    async def copy_element(cls, old_page_id, new_page_id, user):
        old_element_list, new_element_list = await cls.filter(page_id=old_page_id).all(), []
        for index, element in enumerate(old_element_list):
            element_dict = dict(element)
            element_dict.pop("id")
            element_dict["num"], element_dict["page_id"] = index, new_page_id
            element_dict["create_user"] = element_dict["update_user"] = user.id
            new_element_list.append(cls(**element_dict))
        await cls.bulk_create(new_element_list)


class BaseCaseSuite(BaseModel):
    """ 用例集基类表 """
    name = fields.CharField(255, default="", description="用例集名称")
    num = fields.IntField(null=True, default=None, description="用例集在对应服务下的序号")
    suite_type = fields.CharEnumField(
        ApiCaseSuiteTypeEnum, default=ApiCaseSuiteTypeEnum.BASE,
        description="用例集类型，base: 基础用例集，api: 单接口用例集，process: 流程用例集，assist: 造数据用例集")
    parent = fields.IntField(null=True, default=None, description="父级用例集id")
    project_id = fields.IntField(index=True, description="所属的服务id")

    class Meta:
        abstract = True  # 不生成表

    @classmethod
    async def upload(cls, project_id, data_tree, case_model):
        """ 上传用例集 """
        suite_pass, suite_fail, case_pass, case_fail = [], [], [], []
        topic_list = data_tree.get("topic", {}).get("topics", [])

        async def insert_data(topic_data, parent=None):
            title = topic_data.get("title", "")

            if title.startswith('tc'):  # 用例
                case_name = title.split(':')[1] if ':' in title else title.split('：')[1]  # 支持中英文的冒号
                if await case_model.filter(name=case_name, suite_id=parent).first() is None:  # 有才导入
                    desc = topic_data.get("topics", [{}])[0].get("title", case_name)
                    try:
                        await case_model.create(name=case_name, desc=desc, suite_id=parent)
                        case_pass.append(case_name)
                    except:
                        case_fail.append(case_name)
            else:  # 用例集
                suite = await cls.filter(parent=parent, name=title, project_id=project_id).first()
                if suite is None:  # 有就插入下级
                    try:
                        suite = await cls.create(name=title, project_id=project_id, parent=parent, suite_type="process")
                        suite_pass.append(title)
                    except:
                        suite_fail.append(title)
                        return
                for child in topic_data.get("topics", []):
                    await insert_data(child, suite.id)

        for topic_data in topic_list:
            await insert_data(topic_data)

        return {
            "suite": {
                "pass": {
                    "total": len(suite_pass),
                    "data": suite_pass
                },
                "fail": {
                    "total": len(suite_fail),
                    "data": suite_fail
                },
            },
            "case": {
                "pass": {
                    "total": len(case_pass),
                    "data": case_pass
                },
                "fail": {
                    "total": len(case_fail),
                    "data": case_fail
                },
            }
        }

    async def update_children_suite_type(self):
        """ 递归更新子用例集的类型 """
        cls = self.__class__

        async def change_child_suite_type(parent_id):
            child_list = await cls.filter(parent=parent_id).all()
            for child in child_list:
                await cls.filter(id=child.id).update(suite_type=self.suite_type)
                await change_child_suite_type(child.id)

        await change_child_suite_type(self.id)

    @classmethod
    async def create_suite_by_project(cls, project_id):
        """ 根据项目id，创建用例集 """
        project_type, suite_type_list = "ui", ui_suite_list
        if "api" in cls.__name__.lower():
            project_type, suite_type_list = "api", api_suite_list

        model_list = [
            cls(num=index, project_id=project_id, name=suite_type["value"], suite_type=suite_type["key"])
            for index, suite_type in enumerate(suite_type_list)
        ]
        await cls.bulk_create(model_list)

    async def get_run_case_id(self, case_model, business_id=None):
        """ 获取用例集下，状态为要运行的用例id """
        filter_dict = {"suite_id": self.id, "status": CaseStatusEnum.DEBUG_PASS_AND_RUN.value}
        if business_id:
            filter_dict["business_id"] = business_id
        case_list = await case_model.filter(**filter_dict).order_by("num").all().values('id')
        return [case["id"] for case in case_list]

    @classmethod
    async def get_case_id(cls, case_model, project_id: int, suite_id: list, case_id: list):
        """
        获取要执行的用例的id
            1、即没选择用例，也没选择用例集
            2、只选择了用例
            3、只选了用例集
            4、选定了用例和用例集
        """
        # 1、只选择了用例，则直接返回用例
        if len(case_id) != 0 and len(suite_id) == 0:
            return case_id

        # 2、没有选择用例集和用例，则视为选择了所有用例集
        elif len(suite_id) == 0 and len(case_id) == 0:
            suite_list = await cls.filter(
                project_id=project_id, suite_type__in=['api', 'process']).all().values("id")
            suite_id = [suite["id"] for suite in suite_list]

        # 解析已选中的用例集，并继承已选中的用例列表，再根据用例id去重
        case_id_list = await case_model.filter(suite_id__in=suite_id,
                                               status=CaseStatusEnum.DEBUG_PASS_AND_RUN).order_by("num").all().values(
            "id")
        case_id.extend([case_id["id"] for case_id in case_id_list])
        return list(set(case_id))

    @classmethod
    async def get_make_data_case(cls, project_id, case_model):
        """ 获取造数据用例集下的用例 """
        suite_list = await cls.filter(project_id=project_id, suite_type=ApiCaseSuiteTypeEnum.MAKE_DATA).all().values(
            "id")
        suite_id_list = [suite["id"] for suite in suite_list]
        return await case_model.filter(
            suite_id__in=suite_id_list, status=CaseStatusEnum.DEBUG_PASS_AND_RUN).order_by("num").all()


class BaseCase(BaseModel):
    """ 用例基类表 """

    name = fields.CharField(255, default="", description="用例名称")
    num = fields.IntField(null=True, default=None, description="用例序号")
    desc = fields.TextField(default=None, description="用例描述")
    status = fields.IntField(
        default=CaseStatusEnum.NOT_DEBUG_AND_NOT_RUN.value,
        description="用例状态，0未调试-不执行，1调试通过-要执行，2调试通过-不执行，3调试不通过-不执行，默认未调试-不执行")
    run_times = fields.IntField(null=True, default=1, description="执行次数，默认执行1次")
    script_list = fields.JSONField(default=[], description="用例需要引用的脚本list")
    variables = fields.JSONField(
        default=[{"key": "", "value": "", "remark": "", "data_type": ""}], description="用例级的公共参数")
    output = fields.JSONField(default=[], description="用例出参（步骤提取的数据）")
    skip_if = fields.JSONField(
        default=[
            {
                "skip_type": "and", "data_source": None, "check_value": None, "comparator": None, "data_type": None,
                "expect": None
            }
        ],
        description="是否跳过的判断条件")
    suite_id = fields.IntField(index=True, description="所属的用例集id")

    class Meta:
        abstract = True  # 不生成表

    async def delete_case(self, step_model):
        """ 删除用例和用例下的步骤 """
        await step_model.filter(case_id=self.id).delete()
        await self.__class__.filter(id=self.id).delete()

    @classmethod
    def get_quote_case_from(cls, case_id, project_model, suite_model, case_model):
        """ 获取用例的归属 """
        case = case_model.get_first(id=case_id)
        suite_path_name = suite_model.get_from_path(case.suite_id)
        suite = suite_model.get_first(id=case.suite_id)
        project = project_model.get_first(id=suite.project_id)
        return f'{project.name}/{suite_path_name}/{case.name}'

    @classmethod
    async def merge_variables(cls, from_case_id, to_case_id):
        """ 当用例引用的时候，自动将被引用用例的自定义变量合并到发起引用的用例上 """
        if from_case_id:
            from_case, to_case = await cls.filter(id=from_case_id).first(), await cls.filter(id=to_case_id).first()
            from_case_variables = {variable["key"]: variable for variable in from_case.variables}
            to_case_variables = {variable["key"]: variable for variable in to_case.variables}

            for from_variable_key, from_case_variable in from_case_variables.items():
                to_case_variables.setdefault(from_variable_key, from_case_variable)

            await to_case.model_update({"variables": [value for key, value in to_case_variables.items() if key]})

    @classmethod
    async def merge_output(cls, case_id, source_list=[]):
        """ 把步骤的数据提取加到用例的output字段下 """
        output_dict = {}
        for source in source_list:
            if isinstance(source, int):  # 用例id
                source = dict(await cls.filter(id=source).first())
            elif isinstance(source, dict) is False:  # 对象（步骤或用例）
                source = dict(source)

            if source.get("quote_case") or source.get("suite_id"):  # 更新源是用例（引用用例和复制用例下的所有步骤）
                source_id = source["id"] if source.get("suite_id") else source["quote_case"]
                source_case = await cls.filter(id=source_id).first()
                source_case_output = parse_list_to_dict(source_case.output)
                output_dict.update(source_case_output)
            else:  # 更新源为步骤（添加步骤和复制其他用例的步骤）
                output_dict.update(parse_list_to_dict(source["extracts"]))

        to_case = await cls.filter(id=case_id).first()
        output_dict.update(parse_list_to_dict(to_case.output))
        await cls.filter(id=case_id).update(output=parse_dict_to_list(output_dict, False))


class BaseStep(BaseModel):
    """ 测试步骤基类表 """

    name = fields.CharField(255, default="", description="步骤名称")
    num = fields.IntField(null=True, default=0, description="步骤序号，执行顺序按此序号来")
    status = fields.CharEnumField(DataStatusEnum, default=DataStatusEnum.ENABLE,
                                  description="是否执行此步骤, enable/disable，默认enable")
    run_times = fields.IntField(default=1, description="执行次数，默认执行1次")
    up_func = fields.JSONField(default=[], description="步骤执行前的函数")
    down_func = fields.JSONField(default=[], description="步骤执行后的函数")
    skip_if = fields.JSONField(
        default=[
            {
                "skip_type": "and", "data_source": None, "check_value": None, "comparator": None, "data_type": None,
                "expect": None
            }
        ],
        description="是否跳过的判断条件")
    skip_on_fail = fields.IntField(default=1, description="当用例有失败的步骤时，是否跳过此步骤，1跳过，0不跳过，默认跳过")
    data_driver = fields.JSONField(default=[], description="数据驱动，若此字段有值，则走数据驱动的解析")
    quote_case = fields.IntField(null=True, default=None, description="引用用例的id")
    case_id = fields.IntField(index=True, description="步骤所在的用例的id")

    class Meta:
        abstract = True  # 不生成表

    @classmethod
    async def set_has_step_for_step(cls, step_list, case_model):
        """ 增加步骤下是否有步骤的标识（是否为引用用例，为引用用例的话，该用例下是否有步骤）"""
        data_list = []
        for step in step_list:
            if isinstance(step, dict) is False:
                step = dict(step)

            if step["quote_case"]:  # 若果是引用用例，把对应用例的入参出参、用例来源一起返回
                case = await case_model.filter(id=step["quote_case"]).first()
                if case:  # 如果手动从数据库删过数据，可能没有
                    step["children"] = []
                    step["desc"] = case.desc
                    step["skip_if"] = case.skip_if
                    step["variables"] = case.variables
                    step["output"] = case.output

            data_list.append(step)
        return data_list

    @classmethod
    async def set_has_step_for_case(cls, case_list):
        """ 增加是否有步骤的标识 """
        data_list = []
        for case in case_list:
            if isinstance(case, dict) is False:
                case = dict(case)
            step = await cls.filter(case_id=case["id"]).first()
            case["hasStep"] = step is not None
            case["children"] = []
            data_list.append(case)
        return data_list


class BaseTask(BaseModel):
    """ 定时任务基类表 """

    name = fields.CharField(255, default="", description="任务名称")
    num = fields.IntField(null=True, default=0, description="任务序号")

    env_list = fields.JSONField(default=[], description="运行环境")
    case_ids = fields.JSONField(default=[], description="用例id")
    task_type = fields.CharField(16, default="cron", description="定时类型")
    cron = fields.CharField(128, description="cron表达式")
    is_send = fields.CharEnumField(
        SendReportTypeEnum, default=SendReportTypeEnum.NOT_SEND, description="是否发送报告，not_send/always/on_fail")
    receive_type = fields.CharEnumField(
        ReceiveTypeEnum, default=ReceiveTypeEnum.DING_DING, description="接收测试报告类型: ding_ding、we_chat、email")
    webhook_list = fields.JSONField(default=[], description="机器人地址")
    email_server = fields.CharField(255, null=True, default=None, description="发件邮箱服务器")
    email_from = fields.CharField(255, null=True, default=None, description="发件人邮箱")
    email_pwd = fields.CharField(255, null=True, default=None, description="发件人邮箱密码")
    email_to = fields.JSONField(default=[], description="收件人邮箱")
    status = fields.CharEnumField(
        DataStatusEnum, default=DataStatusEnum.DISABLE, description="任务的启用状态, enable/disable，默认disable")
    is_async = fields.IntField(default=0, description="任务的运行机制，0：串行，1：并行，默认0")
    suite_ids = fields.JSONField(default=[], description="用例集id")
    call_back = fields.JSONField(default=[], description="回调给流水线")
    project_id = fields.IntField(index=True, description="所属的服务id")
    conf = fields.JSONField(
        default={"browser": "chrome", "server_id": "", "phone_id": "", "no_reset": ""},
        description="运行配置，webUi存浏览器，appUi存运行服务器、手机、是否重置APP")

    class Meta:
        abstract = True  # 不生成表


class BaseReport(BaseModel):
    """ 测试报告基类表 """

    name = fields.CharField(128, description="测试报告名称")
    is_passed = fields.IntField(default=1, description="是否全部通过，1全部通过，0有报错")
    is_async = fields.IntField(default=0, description="任务的运行机制，0：用例维度串行执行，1：用例维度并行执行")
    run_type = fields.CharField(16, default="task", description="报告类型，task/suite/case/api")
    status = fields.IntField(default=1, description="当前节点是否执行完毕，1执行中，2执行完毕")
    retry_count = fields.IntField(default=0, description="已经执行重试的次数")
    env = fields.CharField(128, default="test", description="运行环境")
    temp_variables = fields.JSONField(null=True, default={}, description="临时参数")
    process = fields.IntField(default=1, description="进度节点, 1: 解析数据、2: 执行测试、3: 写入报告")
    trigger_type = fields.CharEnumField(
        TriggerTypeEnum, default=TriggerTypeEnum.PAGE, description="触发类型，pipeline:流水线、page:页面、cron:定时任务")
    batch_id = fields.CharField(128, index=True, description="运行批次id，用于查询报告")
    run_id = fields.JSONField(description="运行id，用于触发重跑接口/用例/用例集/任务")
    project_id = fields.IntField(index=True, description="所属的服务id")
    summary = fields.JSONField(default={}, description="报告的统计")

    class Meta:
        abstract = True  # 不生成表

    @staticmethod
    def get_summary_template():
        return {
            "result": "success",
            "stat": {
                "test_case": {  # 用例维度
                    "total": 1,  # 初始化的时候给个1，方便用户查看运行中的报告，后续会在流程中更新为实际的total
                    "success": 0,
                    "fail": 0,
                    "error": 0,
                    "skip": 0
                },
                "test_step": {  # 步骤维度
                    "total": 0,
                    "success": 0,
                    "fail": 0,
                    "error": 0,
                    "skip": 0
                },
                "count": {  # 此次运行有多少接口/元素
                    "api": 1,
                    "step": 1,
                    "element": 0
                }
            },
            "time": {  # 时间维度
                "start_at": "",
                "end_at": "",
                "step_duration": 0,  # 所有步骤的执行耗时，只统计请求耗时
                "case_duration": 0,  # 所有用例下所有步骤执行耗时，只统计请求耗时
                "all_duration": 0  # 开始执行 - 执行结束 整个过程的耗时，包含测试过程中的数据解析、等待...
            },
            "env": {  # 环境
                "code": "",
                "name": "",
            }
        }

    @classmethod
    def get_batch_id(cls, user_id):
        """ 生成运行批次id """
        return f'{user_id}_{int(time.time() * 1000000)}'

    @classmethod
    async def get_new_report(cls, **kwargs):
        """ 生成一个测试报告 """
        if "summary" not in kwargs:
            kwargs["summary"] = cls.get_summary_template()
        return await cls.create(**kwargs)

    def merge_test_result(self, case_summary_list):
        """ 汇总测试数据和结果
        Args:
            case_summary_list (list): list of (testcase, result)
        """
        case_result = []
        total_case = len(case_summary_list)
        self.summary["stat"]["test_case"]["total"] = total_case
        self.summary["time"]["start_at"] = case_summary_list[0]["time"][
            "start_at"] if total_case > 0 else datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        for case_summary in case_summary_list:
            case_result.append(case_summary["result"])
            self.summary["stat"]["test_case"][case_summary["result"]] += 1
            self.summary["stat"]["test_step"]["total"] += case_summary["stat"]["total"]
            self.summary["stat"]["test_step"]["fail"] += case_summary["stat"]["fail"]
            self.summary["stat"]["test_step"]["error"] += case_summary["stat"]["error"]
            self.summary["stat"]["test_step"]["skip"] += case_summary["stat"]["skip"]
            self.summary["stat"]["test_step"]["success"] += case_summary["stat"]["success"]
            self.summary["time"]["step_duration"] += case_summary["time"]["step_duration"]
            self.summary["time"]["case_duration"] += case_summary["time"]["case_duration"]

        self.summary["result"] = "error" if "error" in case_result else "fail" if "fail" in case_result else "success"
        return self.summary

    @classmethod
    async def get_last_10_minute_running_count(cls):
        """ 获取最近10分钟产生的，状态为运行中的报告数量，用于判断是否需要把运行任务放到队列中 """
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        last_10_minute = (datetime.datetime.now() + datetime.timedelta(minutes=-10)).strftime("%Y-%m-%d %H:%M:%S")
        return await cls.filter(process__not=3, status__not=2, create_time__range=[last_10_minute, now]).count()

    async def update_report_process(self, **kwargs):
        """ 开始解析数据 """
        await self.__class__.filter(id=self.id).update(**kwargs)

    async def parse_data_start(self):
        """ 开始解析数据 """
        await self.update_report_process(process=1, status=1)

    async def parse_data_finish(self):
        """ 数据解析完毕 """
        await self.update_report_process(process=1, status=2)

    async def run_case_start(self):
        """ 开始运行测试 """
        await self.update_report_process(process=2, status=1)

    async def run_case_finish(self):
        """ 测试运行完毕 """
        await self.update_report_process(process=2, status=2)

    async def save_report_start(self):
        """ 开始保存报告 """
        await self.update_report_process(process=3, status=1)

    async def save_report_finish(self):
        """ 保存报告完毕 """
        await self.update_report_process(process=3, status=2)

    @classmethod
    async def batch_delete_report(cls, report_list):
        """ 批量删除报告 """
        await cls.filter(id__in=report_list).delete()

    @classmethod
    async def clear_case_and_step(cls, report_case_mode, report_step_mode):
        """ 批量删除已删除报告下的用例报告、步骤报告 """
        all_report_list = [report["id"] for report in await cls.all().values("id")]
        await report_case_mode.filter(report_id__not_in=all_report_list).delete()
        await report_step_mode.filter(report_id__not_in=all_report_list).delete()

    async def update_report_result(self, run_result, status=2, summary=None):
        """ 测试运行结束后，更新状态和结果 """
        update_dict = {"is_passed": 1 if run_result == "success" else 0, "status": status}
        if summary:
            update_dict["summary"] = summary
        await self.__class__.filter(id=self.id).update(**update_dict)

    @classmethod
    async def select_is_all_status_by_batch_id(cls, batch_id, process_and_status=[1, 1]):
        """ 查询一个运行批次下离初始化状态最近的报告 """
        status_list = [[1, 1], [1, 2], [2, 1], [2, 2], [3, 1], [3, 2]]
        index = status_list.index(process_and_status)
        for process, status in status_list[index:]:  # 只查传入状态之后的状态
            if await cls.filter(batch_id=batch_id, process=process, status=status).values("id"):
                return {"process": process, "status": status}

    @classmethod
    async def select_is_all_done_by_batch_id(cls, batch_id):
        """ 报告是否全部生成 """
        return await cls.filter(batch_id=batch_id, process__not=3, status__not=2).first() is None

    @classmethod
    async def select_show_report_id(cls, batch_id):
        """ 获取一个运行批次要展示的报告 """
        fail_report = await cls.filter(batch_id=batch_id, is_passed=0).first()
        if fail_report:
            return fail_report.id
        else:
            success_report = await cls.filter(batch_id=batch_id).first()
            return success_report.id


class BaseReportCase(BaseModel):
    """ 用例执行记录基类表 """

    name = fields.CharField(128, description="测试用例名称")
    case_id = fields.IntField(null=True, index=True, description="执行记录对应的用例id, 如果是运行接口，则为null")
    report_id = fields.IntField(index=True, description="测试报告id")
    result = fields.CharField(
        128, default='waite',
        description="步骤测试结果，waite：等待执行、running：执行中、fail：执行不通过、success：执行通过、skip：跳过、error：报错")
    case_data = fields.JSONField(default={}, description="用例的数据")
    summary = fields.JSONField(default={}, description="用例的报告统计")
    error_msg = fields.TextField(default='', description="用例错误信息")

    class Meta:
        abstract = True  # 不生成表

    @staticmethod
    def get_summary_template():
        return {
            "result": "skip",
            "stat": {
                'total': 1,  # 初始化的时候给个1，方便用户查看运行中的报告，后续会在流程中更新为实际的total
                'fail': 0,
                'error': 0,
                'skip': 0,
                'success': 0
            },
            "time": {
                "start_at": "",
                "end_at": "",
                "step_duration": 0,  # 当前用例的步骤执行耗时，只统计请求耗时
                "case_duration": 0,  # 当前用例下所有步骤执行耗时，只统计请求耗时
                "all_duration": 0  # 用例开始执行 - 执行结束 整个过程的耗时，包含测试过程中的数据解析、等待...
            }
        }

    async def save_case_result_and_summary(self):
        """ 保存测试用例的结果和数据 """
        # 耗时
        self.summary["time"]["case_duration"] = round(self.summary["time"]["step_duration"] / 1000, 4)  # 毫秒转秒
        self.summary["time"]["all_duration"] = (
                self.summary["time"]["end_at"] - self.summary["time"]["start_at"]).total_seconds()
        self.summary["time"]["start_at"] = self.summary["time"]["start_at"].strftime("%Y-%m-%d %H:%M:%S.%f")
        self.summary["time"]["end_at"] = self.summary["time"]["end_at"].strftime("%Y-%m-%d %H:%M:%S.%f")

        # 状态
        if self.summary["stat"]["fail"] or self.summary["stat"]["error"]:  # 步骤里面有不通过或者错误，则把用例的结果置为不通过
            self.summary["result"] = "fail"
            await self.test_is_fail(summary=self.summary)
        else:
            self.summary["result"] = "success"
            await self.test_is_success(summary=self.summary)

    @classmethod
    async def get_resport_case_list(cls, report_id, get_summary):
        """ 根据报告id，获取用例列表，性能考虑，只查关键字段 """
        field_list = ["id", "case_id", "name", "result"]
        if get_summary is True:
            field_list.extend(["summary", "case_data", "error_msg"])
        return await cls.filter(report_id=report_id).values(*field_list)

    async def update_report_case_data(self, case_data, summary=None):
        """ 更新测试数据 """
        update_dict = {"case_data": case_data}
        if summary:
            update_dict["summary"] = summary
        await self.__class__.filter(id=self.id).update(**update_dict)

    async def update_report_case_result(self, result, case_data, summary, error_msg):
        """ 更新测试状态 """
        update_dict = {"result": result}
        if case_data:
            update_dict["case_data"] = case_data
        if summary:
            update_dict["summary"] = summary
        if error_msg:
            update_dict["error_msg"] = error_msg
        await self.__class__.filter(id=self.id).update(**update_dict)

    async def test_is_running(self, case_data=None, summary=None):
        await self.update_report_case_result("running", case_data, summary, error_msg=None)

    async def test_is_fail(self, case_data=None, summary=None):
        await self.update_report_case_result("fail", case_data, summary, error_msg=None)

    async def test_is_success(self, case_data=None, summary=None):
        await self.update_report_case_result("success", case_data, summary, error_msg=None)

    async def test_is_skip(self, case_data=None, summary=None):
        await self.update_report_case_result("skip", case_data, summary, error_msg=None)

    async def test_is_error(self, case_data=None, summary=None, error_msg=None):
        await self.update_report_case_result("error", case_data, summary, error_msg)


class BaseReportStep(BaseModel):
    """ 步骤执行记录基类表 """

    name = fields.CharField(128, description="测试步骤名称")
    case_id = fields.IntField(null=True, index=True, default=None, description="步骤所在的用例id")  # 如果是运行的接口，没有用例id
    step_id = fields.IntField(null=True, index=True, default=None, description="步骤id")  # 如果是运行的接口，没有步骤id
    report_case_id = fields.IntField(index=True, description="用例数据id")
    report_id = fields.IntField(index=True, description="测试报告id")
    process = fields.CharField(
        16, default='waite',
        description="步骤执行进度，waite：等待解析、parse: 解析数据、before：前置条件、after：后置条件、run：执行测试、extract：数据提取、validate：断言")
    result = fields.CharField(
        16, default='waite',
        description="步骤测试结果，waite：等待执行、running：执行中、fail：执行不通过、success：执行通过、skip：跳过、error：报错")
    step_data = fields.JSONField(default={}, description="步骤的数据")
    summary = fields.JSONField(
        default={},
        description="步骤的统计")

    class Meta:
        abstract = True  # 不生成表

    @staticmethod
    def get_summary_template():
        return {
            "start_at": "",
            "end_at": "",
            "step_duration": 0,  # 当前步骤执行耗时，只统计请求耗时
            "all_duration": 0  # 当前步骤开始执行 - 执行结束 整个过程的耗时，包含测试过程中的数据解析、等待...
        }

    @classmethod
    async def get_resport_step_list(cls, report_case_id, get_summary):
        """ 获取步骤列表，性能考虑，只查关键字段 """
        field_list = ["id", "case_id", "name", "process", "result"]
        if get_summary is True:
            field_list.extend(["summary"])
        return await cls.filter(report_case_id=report_case_id).values(*field_list)

    async def save_step_result_and_summary(self, step_runner, step_error_traceback=None):
        """ 保存测试步骤的结果和数据 """
        step_data = step_runner.get_test_step_data()
        step_meta_data = step_runner.client_session.meta_data
        step_data["attachment"] = step_error_traceback
        # 保存测试步骤的结果和数据
        await self.update_report_step_data(
            step_data=step_data, result=step_meta_data["result"], summary=step_meta_data["stat"])

    @classmethod
    def add_run_step_result_count(cls, case_summary, step_meta_data):
        """ 记录步骤执行结果数量 """
        match step_meta_data["result"]:
            case "success":
                case_summary["stat"]["success"] += 1
                case_summary["time"]["step_duration"] += step_meta_data["stat"]["elapsed_ms"]
            case "fail":
                case_summary["stat"]["fail"] += 1
                case_summary["time"]["step_duration"] += step_meta_data["stat"]["elapsed_ms"]
            case "error":
                case_summary["stat"]["error"] += 1
            case "skip":
                case_summary["stat"]["skip"] += 1

    async def update_report_step_data(self, **kwargs):
        """ 更新测试数据 """
        await self.__class__.filter(id=self.id).update(**kwargs)

    async def update_test_result(self, result, step_data):
        """ 更新测试状态 """
        update_dict = {"result": result}
        if step_data:
            update_dict["step_data"] = step_data
        await self.__class__.filter(id=self.id).update(**update_dict)

    async def test_is_running(self, step_data=None):
        await self.update_test_result("running", step_data)

    async def test_is_fail(self, step_data=None):
        await self.update_test_result("fail", step_data)

    async def test_is_success(self, step_data=None):
        await self.update_test_result("success", step_data)

    async def test_is_skip(self, step_data=None):
        await self.update_test_result("skip", step_data)

    async def test_is_error(self, step_data=None):
        await self.update_test_result("error", step_data)

    async def update_step_process(self, process, step_data):
        """ 更新数据和执行进度 """
        update_dict = {"process": process}
        if step_data:
            update_dict["step_data"] = step_data

        await self.__class__.filter(id=self.id).update(**update_dict)

    async def test_is_start_parse(self, step_data=None):
        await self.update_step_process("parse", step_data)

    async def test_is_start_before(self, step_data=None):
        await self.update_step_process("before", step_data)

    async def test_is_start_running(self, step_data=None):
        await self.update_step_process("run", step_data)

    async def test_is_start_extract(self, step_data=None):
        await self.update_step_process("extract", step_data)

    async def test_is_start_after(self, step_data=None):
        await self.update_step_process("after", step_data)

    async def test_is_start_validate(self, step_data=None):
        await self.update_step_process("validate", step_data)


class SaveRequestLog(BaseModel):
    """ 记录请求表 """

    ip = fields.CharField(128, null=True, description="访问来源ip")
    url = fields.CharField(128, null=True, description="请求地址")
    method = fields.CharField(10, null=True, description="请求方法")
    headers = fields.JSONField(default={}, description="头部参数")
    params = fields.JSONField(default={}, description="查询字符串参数")
    data_form = fields.JSONField(default={}, description="form_data参数")
    data_json = fields.JSONField(default={}, description="json参数")

    class Meta:
        abstract = True  # 不生成表
