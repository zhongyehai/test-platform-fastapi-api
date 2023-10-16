# -*- coding: utf-8 -*-
import importlib
import types

from app.baseModel import fields, pydantic_model_creator, BaseModel
from app.config.models.runEnv import RunEnv
from utils.util.file_util import FileUtil


class Script(BaseModel):
    """ python脚本 """

    name = fields.CharField(128, index=True, description="脚本名称")
    script_data = fields.TextField(default="", description="脚本代码")
    desc = fields.CharField(128, description="函数文件描述")
    num = fields.IntField(null=True, description="当前函数文件的序号")
    script_type = fields.CharField(
        16, default="test", index=True, description="脚本类型，test：执行测试、mock：mock脚本、encryption：加密、decryption：解密")

    class Meta:
        table = "auto_test_python_script"
        table_description = "python脚本"

    @classmethod
    async def create_script_file(cls, env_code=None, not_create_list=[]):
        """ 创建所有自定义函数 py 文件，默认在第一行加上运行环境
        示例：
            # coding:utf-8

            env_code = "test"

            脚本内容
        """
        if env_code is None:
            env_data = await RunEnv.first()
            env_code = env_data.code

        for script in await cls.all():
            if script.name not in not_create_list:
                FileUtil.save_script_data(f"{env_code}_{script.name}", script.script_data, env_code)

    @classmethod
    async def get_func_by_script_id(cls, script_id_list: list, env_id=None):
        """ 获取指定脚本中的函数 """
        env_data = await RunEnv.first() if env_id is None else await RunEnv.filter(id=env_id).first()
        env_code = env_data.code

        await cls.create_script_file(env_code)  # 创建所有函数文件
        func_dict = {}
        for script_id in script_id_list:
            script = await cls.filter(id=script_id).first()
            func_list = importlib.reload(importlib.import_module(f"script_list.{env_code}_{script.name}"))
            func_dict.update({
                name: item for name, item in vars(func_list).items() if isinstance(item, types.FunctionType)
            })
        return func_dict


ScriptPydantic = pydantic_model_creator(Script, name="Script")
