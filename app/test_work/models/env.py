from app.baseModel import fields, pydantic_model_creator, BaseModel


class Env(BaseModel):
    business = fields.IntField(null=True, description="业务线，如果数据是账号，可以为空")
    name = fields.CharField(255, description="资源名")
    num = fields.IntField(description="序号")
    source_type = fields.CharField(255, description="资源类型，账号:account、地址:addr")
    value = fields.CharField(255, description="数据值")
    password = fields.CharField(255, default='', description="登录密码")
    desc = fields.TextField(default='', description="备注")
    parent = fields.IntField(null=True, description="当source_type为账号时，所属资源id")

    class Meta:
        table = "test_work_env"
        table_description = "环境地址、账号管理表"


EnvPydantic = pydantic_model_creator(Env, name="Env")
