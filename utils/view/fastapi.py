from fastapi import FastAPI as _FastAPI
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from utils.log import logger


class FastAPI(_FastAPI):
    """ 重写fastapi """
    request_id = None  # 记录request_id，方便跟踪链路查问题

    def restful_result(self, code, message, data, **kwargs):
        response_content = jsonable_encoder({"status": code, "message": message, "data": data, **kwargs})
        if (isinstance(data, dict) and data.get("total")) is False:  # 非获取列表的请求非{"data": [], "total": 1}格式，打日志
            logger.info(f'【{self.request_id}】: \n响应参数：{response_content}')
        return JSONResponse(status_code=200 if code != 500 else 500, content=response_content)

    def success(self, msg=None, data=None, **kwargs):
        """ 业务处理成功的响应 """
        return self.restful_result(code=200, message=msg or "处理成功", data=data, **kwargs)

    def trigger_success(self, data=None, **kwargs):
        """ 触发运行成功的响应 """
        return self.success(msg="触发执行成功，请等待执行完毕", data=data, **kwargs)

    def get_success(self, data=None, **kwargs):
        """ 数据获取成功的响应 """
        return self.success(msg="获取成功", data=data, **kwargs)

    def post_success(self, data=None, **kwargs):
        """ 数据新增成功的响应 """
        return self.success(msg="新增成功", data=data, **kwargs)

    def put_success(self, data=None, **kwargs):
        """ 数据修改成功的响应 """
        return self.success(msg="修改成功", data=data, **kwargs)

    def delete_success(self, data=None, **kwargs):
        """ 数据删除成功的响应 """
        return self.success(msg="删除成功", data=data, **kwargs)

    def fail(self, msg=None, data=None, **kwargs):
        """ 业务处理失败的响应 """
        return self.restful_result(code=400, message=msg or "处理失败", data=data, **kwargs)

    def not_login(self, msg=None, data=None, **kwargs):
        """ 未登录的响应 """
        return self.restful_result(code=401, message=msg or "请重新登录", data=data, **kwargs)

    def forbidden(self, msg=None, data=None, **kwargs):
        """ 权限不足 """
        return self.restful_result(code=403, message=msg or "权限不足", data=data, **kwargs)

    def need_reset_password(self, msg=None, data=None, **kwargs):
        """ 需要重置密码 """
        return self.restful_result(code=4003, message=msg or "请重置密码", data=data, **kwargs)

    def url_not_find(self, msg=None, data=None, **kwargs):
        """ url不存在 """
        return self.restful_result(code=404, message=msg or "url不存在", data=data, **kwargs)

    def method_not_allowed(self, msg=None, data=None, **kwargs):
        """ 请求方法错误 """
        return self.restful_result(code=405, message=msg or "请求方法错误", data=data, **kwargs)

    def error(self, msg=None, data=None, **kwargs):
        """ 系统发送错误的响应 """
        return self.restful_result(code=500, message=msg or "系统出错了，请联系开发人员查看", data=data, **kwargs)
