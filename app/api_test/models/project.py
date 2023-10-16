# -*- coding: utf-8 -*-
from ...baseModel import fields, pydantic_model_creator, BaseProject, BaseProjectEnv


class ApiProject(BaseProject):
    """ 服务表 """

    swagger = fields.CharField(255, null=True, default=None, description="服务对应的swagger地址")
    last_pull_status = fields.IntField(null=True, default=1, description="最近一次swagger拉取状态，0拉取失败，1未拉取，2拉取成功")

    class Meta:
        table = "api_test_project"
        table_description = "接口测试服务表"

    async def last_pull_is_fail(self):
        """ 最近一次从swagger拉取失败 """
        await self.model_update({"last_pull_status": 0})

    async def last_pull_is_success(self):
        """ 最近一次从swagger拉取成功 """
        await self.model_update({"last_pull_status": 2})


class ApiProjectEnv(BaseProjectEnv):
    """ 服务环境表 """

    headers = fields.JSONField(default=[{"key": None, "value": None, "remark": None}], description="服务的公共头部信息")

    class Meta:
        table = "api_test_project_env"
        table_description = "接口测试服务环境表"

    # @classmethod
    # def create_env(cls, project_id=None, env_list=None):
    #     """
    #     当环境配置更新时，自动给项目/环境增加环境信息
    #     如果指定了项目id，则只更新该项目的id，否则更新所有项目的id
    #     如果已有当前项目的信息，则用该信息创建到指定的环境
    #     """
    #     if not project_id and not env_list:
    #         return
    #
    #     env_id_list = env_list or RunEnv.get_id_list()
    #
    #     if project_id:
    #         current_project_env = cls.get_first(project_id=project_id)
    #         if current_project_env:
    #             data = current_project_env.to_dict()
    #         else:
    #             data = {"project_id": project_id}
    #
    #         for env_id in env_id_list:
    #             data["env_id"] = env_id
    #             cls().create(data)
    #     else:
    #         all_project = ApiProject.get_all()
    #         for project in all_project:
    #             cls.create_env(project.id, env_id_list)


ApiProjectPydantic = pydantic_model_creator(ApiProject, name="ApiProject")
ApiProjectEnvPydantic = pydantic_model_creator(ApiProjectEnv, name="ApiProjectEnv")
