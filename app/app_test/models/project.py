from app.baseModel import fields, pydantic_model_creator, BaseProject, BaseProjectEnv
from app.config.models.runEnv import RunEnv


class AppUiProject(BaseProject):
    """ APP表 """

    app_package = fields.CharField(255, null=True, description="被测app包名")
    app_activity = fields.CharField(255, null=True, description="被测app要启动的AndroidActivity")
    template_device = fields.IntField(null=True, description="元素定位时参照的设备")

    class Meta:
        table = "app_ui_test_project"
        table_description = "APP测试项目表"


class AppUiProjectEnv(BaseProjectEnv):
    """ APP环境表 """

    class Meta:
        table = "app_ui_test_project_env"
        table_description = "APP测试项目环境表"


AppUiProjectPydantic = pydantic_model_creator(AppUiProject, name="AppUiProject")
AppUiProjectEnvPydantic = pydantic_model_creator(AppUiProjectEnv, name="AppUiProjectEnv")
