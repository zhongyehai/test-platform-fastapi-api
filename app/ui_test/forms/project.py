from typing import Optional, Union, List
from pydantic import Field
from fastapi import Request

from ...baseForm import BaseForm, PaginationForm, ValidateModel
from ..model_factory import WebUiProject as Project, WebUiProjectEnv as ProjectEnv, WebUiModule as Module, \
    WebUiCaseSuite as CaseSuite, WebUiTask as Task
from app.system.models.user import User
from app.assist.models.script import Script


class FindProjectListForm(PaginationForm):
    """ 查找项目form """
    name: Optional[str] = Field(title="项目名")
    manager: Optional[Union[int, str]] = Field(title="负责人")
    business_id: Optional[int] = Field(title="所属业务线")
    create_user: Optional[Union[int, str]] = Field(title="创建者")

    def get_query_filter(self, *args, **kwargs):
        """ 查询条件 """
        user, filter_dict = kwargs.get("user"), {}

        if self.business_id:  # 传了业务线id，就获取对应的业务线的项目
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
    """ 获取具体项目信息 """
    id: int = Field(..., title="项目id")

    async def validate_project_is_exist(self):
        return await self.validate_data_is_exist(f"项目不存在", Project, id=self.id)

    async def validate_request(self, request: Request, *args, **kwargs):
        return await self.validate_project_is_exist()


class DeleteProjectForm(GetProjectForm):
    """ 删除项目 """

    async def validate_request(self, request: Request, *args, **kwargs):
        project = await self.validate_project_is_exist()

        # 删除权限判断，管理员、数据创建者、项目负责人
        if User.is_not_admin(request.state.user.api_permissions):
            if project.create_user != request.state.user.id:
                if project.manager != request.state.user.id:
                    raise ValueError("当前用户无权限删除此项目")

        # 项目下是否有模块
        await self.validate_data_is_not_exist("请先去【页面管理】删除项目下的模块", Module, project_id=self.id)
        await self.validate_data_is_not_exist("请先去【用例管理】删除项目下的用例集", CaseSuite, project_id=self.id)
        await self.validate_data_is_not_exist("请先去【任务管理】删除项目下的任务", Task, project_id=self.id)
        return project


class AddProjectForm(BaseForm):
    """ 添加项目参数校验 """
    name: str = Field(..., min_length=1, max_length=Project.filed_max_length("name"), title="项目名")
    manager: int = Field(..., title="负责人")
    business_id: int = Field(..., title="业务线")
    script_list: Optional[list] = Field(title="要使用的脚本")

    async def validate_request(self, request: Request, *args, **kwargs):
        await self.validate_data_is_not_exist(f"项目名【{self.name}】已存在", Project, name=self.name)
        await self.validate_data_is_exist("负责人对应的用户不存在", User, id=self.manager)


class EditProjectForm(GetProjectForm, AddProjectForm):
    """ 修改项目参数校验 """

    async def validate_request(self, request: Request, *args, **kwargs):
        project = await self.validate_project_is_exist()
        await self.validate_data_is_not_repeat(f"项目名【{self.name}】已存在", Project, self.id, name=self.name)
        await self.validate_data_is_exist("负责人对应的用户不存在", User, id=self.manager)
        return project


class GetEnvForm(BaseForm):
    """ 查找项目环境form """
    project_id: int = Field(..., title="项目id")
    env_id: int = Field(..., title="环境id")

    async def validate_env_is_exist(self):
        return await self.validate_data_is_exist(
            "环境不存在", ProjectEnv, env_id=self.env_id, project_id=self.project_id)

    async def validate_request(self, request: Request, *args, **kwargs):
        env_data = await self.validate_env_is_exist()
        if not env_data:  # 如果没有就插入一条记录， 并且自动同步当前项目已有的环境数据
            env_data = await ProjectEnv.insert_env(self.project_id, self.env_id, request.state.user.id)
        return env_data


class EditEnvForm(GetEnvForm):
    """ 修改环境 """
    id: int = Field(..., title="环境数据id")
    host: str = Field(..., title="域名")
    variables: List[ValidateModel] = Field(title="变量")

    async def validate_request(self, *args, **kwargs):
        env = await self.validate_env_is_exist()

        # 校验公共变量
        project = await Project.filter(id=self.project_id).first()
        all_func_name = await Script.get_func_by_script_id(project.script_list)
        all_variables = {variable.key: variable.value for variable in self.variables if variable.key}
        variables = [variable.dict() for variable in self.variables]
        self.validate_variable_format(variables)
        self.validate_func(all_func_name, content=self.dumps(variables))  # 校验引用的自定义函数
        self.validate_variable(all_variables, self.dumps(variables), "自定义变量")  # 校验变量
        return env


class SynchronizationEnvForm(BaseForm):
    """ 同步环境form """
    project_id: int = Field(..., title="项目id")
    env_from: int = Field(..., title="环境数据源")
    env_to: list = Field(..., title="要同步到环境")

    async def validate_request(self, request: Request, *args, **kwargs):
        await self.validate_data_is_exist("项目不存在", Project, id=self.project_id)
        return await self.validate_data_is_exist(
            "环境不存在", ProjectEnv, project_id=self.project_id, env_id=self.env_from)
