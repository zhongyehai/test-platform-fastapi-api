from app.baseModel import fields, pydantic_model_creator, BaseProject, BaseProjectEnv
from app.config.models.runEnv import RunEnv


class WebUiProject(BaseProject):
    """ 服务表 """

    class Meta:
        table = "web_ui_test_project"
        table_description = "web-ui测试项目表"


class WebUiProjectEnv(BaseProjectEnv):
    """ 服务环境表 """

    class Meta:
        table = "web_ui_test_project_env"
        table_description = "web-ui测试项目环境表"


WebUiProjectPydantic = pydantic_model_creator(WebUiProject, name="WebUiProject")
WebUiProjectEnvPydantic = pydantic_model_creator(WebUiProjectEnv, name="WebUiProjectEnv")
