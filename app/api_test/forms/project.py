from typing import Optional, Union, List
from pydantic import Field
import validators

from ...assist.models.script import Script
from ...baseForm import BaseForm, PaginationForm, ValidateModel, HeaderModel
from ..model_factory import ApiProject as Project, ApiProjectEnv as ProjectEnv, ApiModule as Module, \
    ApiCaseSuite as Suite, ApiTask as Task
from ...system.model_factory import User


class FindProjectListForm(PaginationForm):
    """ 查找服务form """
    name: Optional[str] = Field(title="服务名")
    manager: Optional[Union[int, str]] = Field(title="负责人")
    business_id: Optional[int] = Field(title="所属业务线")
    create_user: Optional[Union[int, str]] = Field(title="创建者")

    def get_query_filter(self, *args, **kwargs):
        """ 查询条件 """
        user, filter_dict = kwargs.get("user"), {}

        if self.business_id:  # 传了业务线id，就获取对应的业务线的服务
            filter_dict["business_id"] = self.business_id
        else:
            if User.is_not_admin(user.api_permissions):  # 非管理员
                filter_dict["business_id__in"] = user.business_list

        if self.name:
            filter_dict["name__icontains"] = self.name
        if self.manager:
            filter_dict["manager"] = self.manager
        if self.business_id:
            filter_dict["business_id"] = self.business_id
        if self.create_user:
            filter_dict["create_user"] = self.create_user
        return filter_dict


class GetProjectForm(BaseForm):
    """ 获取具体服务信息 """
    id: int = Field(..., title="服务id")

    async def validate_project_is_exist(self):
        return await self.validate_data_is_exist("服务不存在", Project, id=self.id)

    async def validate_request(self, *args, **kwargs):
        return await self.validate_project_is_exist()


class DeleteProjectForm(GetProjectForm):
    """ 删除服务 """

    async def validate_request(self, user, *args, **kwargs):
        project = await self.validate_project_is_exist()

        # 删除权限判断，管理员、数据创建者、服务负责人
        if User.is_not_admin(user.api_permissions):
            if user.id not in [project.create_user, project.manager]:
                raise ValueError("当前用户无权限删除此服务")

        # 服务下是否有模块
        await self.validate_data_is_not_exist("请先去【页面管理】删除服务下的模块", Module, project_id=self.id)
        await self.validate_data_is_not_exist("请先去【用例管理】删除服务下的用例集", Suite, project_id=self.id)
        await self.validate_data_is_not_exist("请先去【任务管理】删除服务下的任务", Task, project_id=self.id)
        return project


class AddProjectForm(BaseForm):
    """ 添加服务参数校验 """
    name: str = Field(..., min_length=1, max_length=Project.filed_max_length("name"), title="服务名")
    manager: int = Field(..., title="负责人")
    business_id: int = Field(..., title="业务线")
    swagger: Optional[str] = Field(title="swagger地址")
    script_list: Optional[list] = Field(title="要使用的脚本")

    def validate_swagger(self):
        """ 校验swagger地址 """
        if self.swagger:
            self.validate_is_true(f"swagger地址不正确，请输入正确地址", validators.url(self.swagger) is True)
            self.validate_is_true(
                f"swagger地址不正确，请输入获取swagger数据的地址，不要输入swagger-ui地址",
                "swagger-ui.htm" not in self.swagger
            )

    async def validate_request(self, *args, **kwargs):
        self.validate_swagger()
        await self.validate_data_is_exist("负责人对应的用户不存在", User, id=self.manager)


class EditProjectForm(GetProjectForm, AddProjectForm):
    """ 修改服务参数校验 """

    async def validate_request(self, *args, **kwargs):
        self.validate_swagger()
        project = await self.validate_project_is_exist()
        await self.validate_data_is_exist("负责人对应的用户不存在", User, id=self.manager)
        return project


class GetEnvForm(BaseForm):
    """ 查找服务环境form """
    project_id: int = Field(..., title="服务id")
    env_id: int = Field(..., title="环境id")

    async def validate_env_is_exist(self):
        return await self.validate_data_is_exist(
            "环境不存在", ProjectEnv, env_id=self.env_id, project_id=self.project_id)

    async def validate_request(self, user, *args, **kwargs):
        env_data = await self.validate_env_is_exist()
        if not env_data:  # 如果没有就插入一条记录， 并且自动同步当前服务已有的环境数据
            env_data = await ProjectEnv.insert_env(self.project_id, self.env_id, user.id)
        return env_data


class EditEnvForm(GetEnvForm):
    """ 修改环境 """
    id: int = Field(..., title="环境数据id")
    host: str = Field(..., title="域名")
    variables: List[ValidateModel] = Field(title="变量")
    headers: List[HeaderModel] = Field(title="头部信息")

    def validate_variables(self, all_func_name, all_variables):
        """ 公共变量参数的校验
        1.校验是否存在引用了自定义函数但是没有引用脚本文件的情况
        2.校验是否存在引用了自定义变量，但是自定义变量未声明的情况
        """
        variables = [variable.dict() for variable in self.variables]
        self.validate_variable_format(variables)  # 校验格式
        self.validate_func(all_func_name, content=self.dumps(variables))  # 校验引用的自定义函数
        self.validate_variable(all_variables, self.dumps(variables), "自定义变量")  # 校验变量

    def validate_headers(self, all_func_name, all_variables):
        """ 头部参数的校验
        1.校验是否存在引用了自定义函数但是没有引用脚本文件的情况
        2.校验是否存在引用了自定义变量，但是自定义变量未声明的情况
        """
        headers = [header.dict() for header in self.headers]
        self.validate_header_format(headers)  # 校验格式
        self.validate_func(all_func_name, content=self.dumps(headers))  # 校验引用的自定义函数
        self.validate_variable(all_variables, self.dumps(headers), "头部信息")  # 校验引用的变量

    async def validate_request(self, *args, **kwargs):
        project_env = await self.validate_env_is_exist()

        project = await self.validate_data_is_exist("服务不存在", Project, id=project_env.project_id)
        all_func_name = await Script.get_func_by_script_id(project.script_list)

        all_variables = {variable.key: variable.value for variable in self.variables if variable.key}
        self.validate_variables(all_func_name, all_variables)
        self.validate_headers(all_func_name, all_variables)
        return project_env


class SynchronizationEnvForm(BaseForm):
    """ 同步环境form """
    project_id: int = Field(..., title="服务id")
    env_from: int = Field(..., title="环境数据源")
    env_to: list = Field(..., title="要同步到环境")

    async def validate_request(self, *args, **kwargs):
        await self.validate_data_is_exist("服务不存在", Project, id=self.project_id)
        return await self.validate_data_is_exist(
            "环境不存在", ProjectEnv, project_id=self.project_id, env_id=self.env_from)
