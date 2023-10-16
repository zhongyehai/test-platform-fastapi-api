from app.baseModel import BaseTask, fields, pydantic_model_creator


class AppUiTask(BaseTask):
    """ 测试任务表 """

    class Meta:
        table = "app_ui_test_task"
        table_description = "APP测试任务表"


AppUiTaskPydantic = pydantic_model_creator(AppUiTask, name="AppUiTask")
