# from loguru import logger
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

from ..log import logger


def restful_result(code, message, data, **kwargs):
    """ 统一返 result风格 """
    response_content = jsonable_encoder({"status": code, "message": message, "data": data, **kwargs})
    if (isinstance(data, dict) and data.get("total")) is False:  # 非获取列表的请求非{"data": [], "total": 1}格式，打日志
        logger.info(response_content)
    return JSONResponse(status_code=200 if code != 500 else 500, content=response_content)


def success(msg=None, data=None, **kwargs):
    """ 业务处理成功的响应 """
    return restful_result(code=200, message=msg or "处理成功", data=data, **kwargs)


def trigger_success(data=None, **kwargs):
    """ 触发运行成功的响应 """
    return success(msg="触发执行成功，请等待执行完毕", data=data, **kwargs)


def get_success(data=None, **kwargs):
    """ 数据获取成功的响应 """
    return success(msg="获取成功", data=data, **kwargs)


def post_success(data=None, **kwargs):
    """ 数据新增成功的响应 """
    return success(msg="新增成功", data=data, **kwargs)


def put_success(data=None, **kwargs):
    """ 数据修改成功的响应 """
    return success(msg="修改成功", data=data, **kwargs)


def delete_success(data=None, **kwargs):
    """ 数据删除成功的响应 """
    return success(msg="删除成功", data=data, **kwargs)


def fail(msg=None, data=None, **kwargs):
    """ 业务处理失败的响应 """
    return restful_result(code=400, message=msg or "处理失败", data=data, **kwargs)


def not_login(msg=None, data=None, **kwargs):
    """ 未登录的响应 """
    return restful_result(code=401, message=msg or "请重新登录", data=data, **kwargs)


def forbidden(msg=None, data=None, **kwargs):
    """ 权限不足 """
    return restful_result(code=403, message=msg or "权限不足", data=data, **kwargs)


def url_not_find(msg=None, data=None, **kwargs):
    """ url不存在 """
    return restful_result(code=404, message=msg or "url不存在", data=data, **kwargs)


def method_not_allowed(msg=None, data=None, **kwargs):
    """ 请求方法错误 """
    return restful_result(code=405, message=msg or "请求方法错误", data=data, **kwargs)


def error(msg=None, data=None, **kwargs):
    """ 系统发送错误的响应 """
    return restful_result(code=500, message=msg or "系统出错了，请联系开发人员查看", data=data, **kwargs)
