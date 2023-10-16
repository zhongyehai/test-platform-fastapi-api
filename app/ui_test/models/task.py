from app.baseModel import BaseTask, fields, pydantic_model_creator


class WebUiTask(BaseTask):
    """ 测试任务表 """

    class Meta:
        table = "web_ui_test_task"
        table_description = "web-ui测试任务表"


WebUiTaskPydantic = pydantic_model_creator(WebUiTask, name="WebUiTask")
