import json
from typing import Optional, List
from pydantic import Field
from fastapi import Request

from ...baseForm import BaseForm, PaginationForm, AddCaseDataForm, VariablesModel, SkipIfModel
from ..model_factory import WebUiProject as Project, WebUiProjectEnv as ProjectEnv, WebUiCaseSuite as CaseSuite, \
    WebUiStep as Step, WebUiCase as Case
from ...assist.models.script import Script
from ...enums import CaseStatusEnum


class FindCaseForm(PaginationForm):
    """ 根据用例集查找用例 """
    name: Optional[str] = Field(title="用例名")
    status: Optional[int] = Field(
        title="用例调试状态",
        description="0未调试-不执行，1调试通过-要执行，2调试通过-不执行，3调试不通过-不执行，默认未调试-不执行")
    has_step: Optional[int] = Field(title="标识用例下是否有步骤")
    suite_id: int = Field(..., title="用例集")

    def get_query_filter(self, *args, **kwargs):
        """ 查询条件 """
        filter_dict = {"suite_id": self.suite_id}
        if self.name:
            filter_dict["name__icontains"] = self.name
        if self.status:
            filter_dict["status"] = self.status
        return filter_dict


class GetAssistCaseForm(BaseForm):
    """ 根据服务查找用例 """
    project_id: int = Field(..., title="服务id")


class GetCaseNameForm(BaseForm):
    """ 获取用例的名字 """
    case_list: List[int] = Field(..., title="用例id list")


class GetCaseForm(BaseForm):
    """ 获取用例信息 """
    id: int = Field(..., title="用例id")

    async def validate_case_is_exist(self):
        return await self.validate_data_is_exist("用例不存在", Case, id=self.id)

    async def validate_request(self, *args, **kwargs):
        return await self.validate_case_is_exist()


class DeleteCaseForm(GetCaseForm):
    """ 删除用例 """

    async def validate_request(self, request: Request, *args, **kwargs):
        case = await self.validate_case_is_exist()
        step = await Step.filter(quote_case=self.id).first()
        if step:
            step_case = await Case.filter(id=step.case_id).first()
            raise ValueError(f"用例【{step_case.name}】已引用此用例，请先解除引用")
        return case


class ChangeCaseStatusForm(BaseForm):
    """ 批量修改用例状态 """
    id_list: List[int] = Field(..., title="用例id list")
    status: CaseStatusEnum = Field(
        ..., title="用例调试状态",
        description="0未调试-不执行，1调试通过-要执行，2调试通过-不执行，3调试不通过-不执行，默认未调试-不执行")

class CopyCaseStepForm(BaseForm):
    """ 复制用例的步骤 """

    from_case: int = Field(..., title="复制源用例id")
    to_case: int = Field(..., title="当前用例id")

    async def validate_request(self, *args, **kwargs):
        self.validate_is_true(
            len(await Case.filter(id__in=[self.from_case, self.to_case]).all()) == 2, "用例不存在")


class PullCaseStepForm(BaseForm):
    """ 拉取当前引用用例的步骤到当前步骤所在的位置 """
    step_id: int = Field(..., title="复制源步骤id")
    case_id: int = Field(..., title="用例id")

    async def validate_request(self, *args, **kwargs):
        step = await self.validate_data_is_exist("步骤不存在", Step, id=self.step_id)
        await self.validate_data_is_exist("用例不存在", Case, id=self.case_id)
        return step


class AddCaseForm(BaseForm):
    """ 添加用例的校验 """
    suite_id: int = Field(..., title="用例集id")
    case_list: List[AddCaseDataForm] = Field(..., title="用例")

    async def validate_request(self, *args, **kwargs):
        await self.validate_data_is_exist("用例集不存在", CaseSuite, id=self.suite_id)

        case_list, name_list, name_length = [], [], Case.filed_max_length("name")
        for index, case in enumerate(self.case_list):
            self.validate_is_true(f'第【{index + 1}】行，用例名必传', case.name)
            self.validate_is_true(f'第【{index + 1}】行，用例名长度不可超过{name_length}位', case.name)
            if case.name in name_list:
                raise ValueError(f'第【{index + 1}】行，与第【{name_list.index(case.name) + 1}】行，用例名重复')
            self.validate_is_true(f'第【{index + 1}】行，用例描述必传', case.desc)

            await self.validate_data_is_not_exist(
                f'第【{index + 1}】行，用例名【{case.name}】已存在', Case, name=case.name, suite_id=self.suite_id)

            case_list.append({"suite_id": self.suite_id, **case.dict()})  # 保存用例数据，并加上用例集id
            name_list.append(case.name)
        return case_list


class EditCaseForm(GetCaseForm):
    """ 修改用例 """
    suite_id: int = Field(..., title="用例集id")
    name: str = Field(..., title="用例名称")
    desc: str = Field(..., title="用例描述")
    script_list: List[int] = Field(default=[], title="引用脚本id")
    skip_if: List[SkipIfModel] = Field(default=[], title="跳过条件")
    variables: List[VariablesModel] = Field(default=[], title="变量")
    run_times: int = Field(1, title="运行次数")

    def validate_variables(self, all_func_name, all_variables):
        """ 公共变量参数的校验
        1.校验是否存在引用了自定义函数但是没有引用脚本文件的情况
        2.校验是否存在引用了自定义变量，但是自定义变量未声明的情况
        """
        variables = [variable.dict() for variable in self.variables]
        self.validate_variable_format(variables)  # 校验格式
        self.validate_func(all_func_name, content=self.dumps(variables))  # 校验引用的自定义函数
        self.validate_variable(all_variables, self.dumps(variables), "自定义变量")  # 校验变量

    async def validate_request(self, request: Request, *args, **kwargs):
        case = await self.validate_case_is_exist()
        await self.validate_data_is_not_repeat(
            f"用例名【{self.name}】已存在", Case, self.id, name=self.name, suite_id=self.suite_id)

        suite = await CaseSuite.filter(id=self.suite_id).first()
        project = await Project.filter(id=suite.project_id).first()
        project_env = await ProjectEnv.filter(id=project.id).first()

        # 合并项目选择的自定义函数和用例选择的脚本文件
        project_script_list = project.script_list
        project_script_list.extend(self.script_list)
        all_func_name = await Script.get_func_by_script_id(project_script_list)

        # 合并环境的变量和case的变量
        variables = project_env.variables
        variables.extend([variable.dict() for variable in self.variables])
        all_variables = {variable.get("key"): variable.get("value") for variable in variables if variable.get("key")}

        self.validate_variables(all_func_name, all_variables)
        return case


class RunCaseForm(BaseForm):
    """ 运行用例 """
    case_id_list: List[int] = Field(..., title="用例id list")
    env_list: List[str] = Field(..., title="运行环境code")
    temp_variables: Optional[dict] = Field(title="临时指定参数")
    is_async: int = Field(default=0, title="执行模式", description="0：用例维度串行执行，1：用例维度并行执行")
    browser: str = Field(default="chrome", title="运行浏览器")
    tigger_type: Optional[str] = Field(default=0, title="触发类型")

    async def validate_request(self, *args, **kwargs):
        case_list = await Case.filter(id__in=self.case_id_list).all()
        self.validate_is_true(len(case_list) > 0, "用例不存在")

        # 公共变量参数的校验
        # 1.校验是否存在引用了自定义函数但是没有引用脚本文件的情况
        # 2.校验是否存在引用了自定义变量，但是自定义变量未声明的情况
        if self.temp_variables and len(self.case_id_list) == 1:
            variables, headers = self.temp_variables.get("variables", []), self.temp_variables.get("headers", [])

            # 1、先校验数据格式
            if len(variables) > 0:  # 校验变量
                self.validate_variable_format(variables)  # 校验格式

            if len(headers) > 0:  # 校验头部参数
                self.validate_header_format(headers)  # 校验格式

            # 2、校验数据引用是否合法
            case = await Case.filter(id=self.case_id_list[0]).first()
            suite = await CaseSuite.filter(id=case.suite_id).first()
            project = await Project.filter(id=suite.project_id).first()

            # 自定义函数
            project_script_list = project.script_list
            project_script_list.extend(case.script_list)
            all_func_name = await Script.get_func_by_script_id(project_script_list)
            self.validate_func(all_func_name, content=self.dumps(variables))  # 校验引用的自定义函数

            # 变量
            env = await ProjectEnv.filter(project_id=project.id).first()
            env_variables = env.variables
            env_variables.extend(case.variables)
            all_variables = {
                variable.get("key"): variable.get("value") for variable in env_variables if variable.get("key")
            }
            if len(variables) > 0:  # 校验变量
                self.validate_variable(all_variables, self.dumps(variables), "自定义变量")  # 校验变量

            if len(headers) > 0:  # 校验头部参数
                self.validate_func(all_func_name, content=self.dumps(headers))  # 校验引用的自定义函数
                self.validate_variable(all_variables, self.dumps(headers), "头部信息")  # 校验引用的变量

        return case_list
