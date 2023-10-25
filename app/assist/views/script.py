import importlib
import sys
import types
import traceback

from typing import List
from fastapi import Request

from ..routers import assist_router
from ...baseForm import ChangeSortForm
from ..model_factory import Script, ScriptPydantic
from ..forms.script import (
    FindScriptForm, GetScriptForm, CreatScriptForm, EditScriptForm, DebugScriptForm, DeleteScriptForm)
from utils.util.file_util import FileUtil
from utils.redirect_print_log import RedirectPrintLogToMemory
from utils.client.test_runner.parser import parse_function, extract_functions


@assist_router.login_post("/script/list", response_model=List[ScriptPydantic], summary="获取脚本文件列表")
async def get_script_list(form: FindScriptForm, request: Request):
    get_filed = [] if form.detail else ["id", "name"]
    query_data = await form.make_pagination(Script, get_filed=get_filed, not_get_filed=["script_data"])
    return request.app.get_success(data=query_data)


@assist_router.login_put("/script/sort", summary="脚本文件列表排序")
async def change_script_sort(form: ChangeSortForm, request: Request):
    await Script.change_sort(**form.dict(exclude_unset=True))
    return request.app.put_success()


@assist_router.login_post("/script/copy", summary="复制自定义脚本文件")
async def copy_script(form: GetScriptForm, request: Request):
    script = await form.validate_request()
    script = await script.copy()
    return request.app.success("复制成功", data=script)


@assist_router.login_post("/script/debug", summary="函数调试")
async def debug_script(form: DebugScriptForm, request: Request):
    script = await form.validate_request()
    name, expression = f'{form.env}_{script.name}', form.expression
    await Script.create_script_file(form.env)  # 把自定义函数脚本内容写入到python脚本中

    # 动态导入脚本
    try:
        import_path = f'script_list.{name}'
        func_list = importlib.reload(importlib.import_module(import_path))
        module_functions_dict = {
            name: item for name, item in vars(func_list).items() if isinstance(item, types.FunctionType)
        }
        ext_func = extract_functions(expression)
        func = parse_function(ext_func[0])

        # 重定向print内容到内存
        redirect = RedirectPrintLogToMemory()
        result = module_functions_dict[func["func_name"]](*func["args"], **func["kwargs"])  # 执行脚本
        script_print = redirect.get_text_and_redirect_to_default()

        return request.app.success(msg="执行成功，请查看执行结果", result={
            "env": form.env,
            "expression": form.expression,
            "result": result,
            "script_print": script_print,
            "script": FileUtil.get_func_data_by_script_name(f'{form.env}_{script.name}')
        })
    except Exception as e:
        sys.stdout = sys.__stdout__  # 恢复输出到console
        # app.logger.info(str(e))
        error_data = "\n".join("{}".format(traceback.format_exc()).split("↵"))
        return request.app.fail(msg="语法错误，请检查", result={
            "env": form.env,
            "expression": form.expression,
            "result": error_data,
            "script": FileUtil.get_func_data_by_script_name(f'{form.env}_{script.name}')
        })


@assist_router.login_post("/script/detail", summary="获取脚本文件详情")
async def get_script(form: GetScriptForm, request: Request):
    script = await form.validate_request()
    return request.app.get_success(data=script)


@assist_router.login_post("/script", summary="新增脚本文件")
async def add_script(form: CreatScriptForm, request: Request):
    await form.validate_request(request.state.user)
    script = await Script.model_create(form.dict(), request.state.user)
    return request.app.post_success({"id": script.id})


@assist_router.login_put("/script", summary="修改脚本文件")
async def update_script(form: EditScriptForm, request: Request):
    script = await form.validate_request(request.state.user)
    await script.model_update(form.dict(), request.state.user)
    return request.app.put_success()


@assist_router.login_delete("/script", summary="删除脚本文件")
async def delete_script(form: DeleteScriptForm, request: Request):
    script = await form.validate_request(request.state.user)
    await script.model_delete()
    return request.app.delete_success()
