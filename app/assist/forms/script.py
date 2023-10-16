import re
import importlib
import traceback

from typing import Optional
from pydantic import Field

from ...baseForm import BaseForm, PaginationForm
from ..model_factory import Script, ScriptPydantic
from ...config.model_factory import Config
from ...api_test.model_factory import ApiProject, ApiCase
from ...ui_test.model_factory import WebUiProject, WebUiCase
from ...app_test.model_factory import AppUiProject, AppUiCase
from utils.util.file_util import FileUtil


class FindScriptForm(PaginationForm):
    """ 查找脚本form """
    detail: Optional[str] = Field(title="是否获取更多数据")
    file_name: Optional[str] = Field(title="脚本名")
    script_type: Optional[int] = Field(title="脚本类型")
    create_user: Optional[int] = Field(title="创建者")
    update_user: Optional[int] = Field(title="修改者")

    def get_query_filter(self, *args, **kwargs):
        """ 查询条件 """
        filter_dict = {}
        if self.file_name:
            filter_dict["file_name__icontains"] = self.file_name
        if self.script_type:
            filter_dict["script_type"] = self.script_type
        if self.create_user:
            filter_dict["create_user"] = self.create_user
        if self.create_user:
            filter_dict["create_user"] = self.create_user
        return filter_dict


class GetScriptForm(BaseForm):
    """ 获取自定义脚本文件 """
    id: int = Field(..., title="脚本文件id")

    async def validate_script_is_exist(self):
        return await self.validate_data_is_exist("脚本不存在", Script, id=self.id)

    async def validate_request(self, *args, **kwargs):
        return await self.validate_script_is_exist()


class DeleteScriptForm(GetScriptForm):
    """ 删除脚本文件 """

    async def validate_request(self, user, *args, **kwargs):
        """
        1.校验自定义脚本文件需存在
        2.校验是否有引用
        3.校验当前用户是否为管理员或者创建者
        """
        script = await self.validate_script_is_exist()

        # 校验是否被引用
        for model in [ApiProject, AppUiProject, WebUiProject, ApiCase, AppUiCase, WebUiCase]:
            data = await model.filter(id=self.id).first()
            if data:
                class_name = model.__name__

                if 'Project' in class_name:
                    name = '服务' if 'Api' in class_name else '项目' if 'WebUi' in class_name else 'APP'
                    raise ValueError(f"{name}【{data.name}】已引用此脚本文件，请先解除依赖再删除")
                else:
                    name = '接口' if 'Api' in class_name else 'WebUi' if 'WebUi' in class_name else 'APP'
                    raise ValueError(f"{name}测试用例【{data.name}】已引用此脚本文件，请先解除依赖再删除")

        # 用户是管理员或者创建者
        self.validate_is_true(
            "脚本文件仅【管理员】或【创建者】可删除",
            self.is_admin(user.api_permissions) or script.is_create_user(user.id))
        return script


class DebugScriptForm(GetScriptForm):
    """ 调试函数 """
    expression: str = Field(..., title="调试表达式")
    env: str = Field(..., title="运行环境")

    async def validate_request(self, *args, **kwargs):
        return await self.validate_script_is_exist()


class CreatScriptForm(BaseForm):
    """ 创建自定义脚本文件 """
    name: str = Field(..., title="脚本文件名")
    script_type: str = Field(..., title="脚本类型")
    desc: Optional[str] = Field(title="脚本描述")
    script_data: str = Field(..., title="脚本内容")

    async def validate_script_name(self, *args, **kwargs):
        """  校验Python脚本文件名 """
        self.validate_is_true(f"脚本文名错误，支持大小写字母和下划线", re.match('^[a-zA-Z_]+$', self.name))
        await self.validate_data_is_not_exist(f"脚本文件【{self.name}】已经存在", Script, name=self.name)

    async def validate_script_data(self, user, *args, **kwargs):
        """ 校验自定义脚本文件内容合法 """
        default_env = 'debug'
        if self.script_data:
            # 校验当前用户是否有权限保存脚本文件内容
            if await Config.get_save_func_permissions() == '1':
                if self.is_not_admin(user.api_permissions):
                    raise ValueError({
                        "msg": "当前用户暂无权限保存脚本文件内容",
                        "result": "当前用户暂无权限保存脚本文件内容"
                    })

            if self.script_type != 'mock':
                # 防止要改函数时不知道函数属于哪个脚本的情况，强校验函数名必须以脚本名开头
                # importlib.import_module有缓存，所有用正则提取
                functions_name_list = re.findall('\ndef (.+?):', self.script_data)

                for func_name in functions_name_list:
                    if func_name.startswith(self.name) is False:
                        raise ValueError(f'函数【{func_name}】命名格式错误，请以【脚本名_函数名】命名')

            # 把自定义函数脚本内容写入到python脚本中,
            await Script.create_script_file(default_env)  # 重新发版时会把文件全部删除，所以全部创建
            FileUtil.save_script_data(f'{default_env}_{self.name}', self.script_data, env=default_env)

            # 动态导入脚本，语法有错误则不保存
            try:
                script_obj = importlib.reload(importlib.import_module(f'script_list.{default_env}_{self.name}'))
            except Exception as e:
                raise ValueError({
                    "msg": "语法错误，请检查",
                    "result": "\n".join("{}".format(traceback.format_exc()).split("↵"))
                })

    async def validate_request(self, user, *args, **kwargs):
        await self.validate_script_name()
        await self.validate_script_data(user)


class EditScriptForm(GetScriptForm, CreatScriptForm):
    """ 修改自定义脚本文件 """

    async def validate_request(self, user, *args, **kwargs):
        script = await self.validate_script_is_exist()
        await self.validate_data_is_not_repeat(f"脚本文件【{self.name}】已经存在", Script, self.id, name=self.name)
        await self.validate_script_data(user)
        return script
