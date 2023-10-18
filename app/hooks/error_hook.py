import platform
import traceback

from pydantic import ValidationError
from fastapi import Request
from fastapi.exceptions import RequestValidationError

from app.system.model_factory import SystemErrorRecord
from utils.message.send_report import send_system_error
from utils.view import restful
from utils.util import request as async_requests


def register_exception_handler(app):
    @app.exception_handler(RequestValidationError)
    async def filed_type_error(request, exc):
        """ pydantic数据类型、必传字段 校验不通过
        [
            # 数据类型错误
            {'loc': ('report_id',), 'msg': 'value is not a valid integer', 'type': 'type_error.integer'},
            # 必传数据
            {'loc': ('from_id',), 'msg': 'field required', 'type': 'value_error.missing'},
            # 主动抛的ValueError
            {'loc': ('report_id',), 'msg': '数据不存在', 'type': 'value_error'}
            # 数据类型错误
            {'loc': ('body', 'permission_id'), 'msg': 'value is not a valid integer', 'type': 'type_error.integer'}
            # 长度错误
            {'ctx': {'limit_value': 4}, 'loc': ('body', 'permission_id'), 'msg': 'ensure this value has at most 4 characters', 'type': 'value_error.any_str.max_length'}
            {'ctx': {'limit_value': 2}, 'loc': ('body', 'permission_id'), 'msg': 'ensure this value has at least 2 characters', 'type': 'value_error.any_str.min_length'}
        ]
        """
        return get_error_msg(exc)

    @app.exception_handler(ValidationError)
    async def filed_validate_error(request, exc):
        """ pydantic数据类型、必传字段 校验不通过 """
        """
        [
            # 数据类型错误
            {'loc': ('report_id',), 'msg': 'value is not a valid integer', 'type': 'type_error.integer'}, 
            # 必传数据
            {'loc': ('from_id',), 'msg': 'field required', 'type': 'value_error.missing'},
            # 主动抛的ValueError
            {'loc': ('report_id',), 'msg': '数据不存在', 'type': 'value_error'}
            # 数据类型错误
            {'loc': ('body', 'permission_id'), 'msg': 'value is not a valid integer', 'type': 'type_error.integer'}
            # 长度错误
            {'ctx': {'limit_value': 4}, 'loc': ('body', 'permission_id'), 'msg': 'ensure this value has at most 4 characters', 'type': 'value_error.any_str.max_length'}
            {'ctx': {'limit_value': 2}, 'loc': ('body', 'permission_id'), 'msg': 'ensure this value has at least 2 characters', 'type': 'value_error.any_str.min_length'}
        ]
        """
        return get_error_msg(exc)

    @app.exception_handler(Exception)
    async def unexpected_exception(request: Request, exc: Exception):
        """ 未预期的所有异常捕获、pydantic数据值校验不通过 """
        if isinstance(exc, ValueError): return restful.fail(str(exc))  # 数据值校验不通过

        error = traceback.format_exc()
        try:
            request.app.logger.error(f'系统报错了:  \n\n url: {request.url} \n\n 错误详情: \n\n {error}')

            # 写数据库
            error_record = await SystemErrorRecord.create(
                url=request.url,
                method=request.method,
                headers=dict(request.headers),
                params=dict(request.query_params) or {},
                data_form={},
                data_json={} if request.url.path.endswith("upload") else request.state.set_body,
                detail=error
            )

            # 发送即时通讯通知
            if platform.platform().startswith('Linux'):
                send_system_error(
                    title=f'{request.app.config["SECRET_KEY"]}报错通知，数据id：{error_record.id}', content=error)
        except Exception as error:
            print(traceback.format_exc())


def get_error_msg(exc):
    # error_msg = exc.errors()
    error = exc.errors()[0]
    filed_name = error["loc"][-1]
    error_type, msg = error["type"], error["msg"]

    if "type_error" in error_type:  # 数据类型错误
        return restful.fail(f'{filed_name} 数据类型错误')

    elif "max_length" in error_type:  # 数据长度超长
        return restful.fail(f'{filed_name} 长度超长，最多{error["ctx"]["limit_value"]}位')

    elif "min_length" in error_type:  # 数据长度超长
        return restful.fail(f'{filed_name} 长度不够，最少{error["ctx"]["limit_value"]}位')

    elif "required" in msg:  # 必传字段
        return restful.fail(f'{filed_name} 必传')

    return restful.fail(msg)  # 数据值验证不通过
