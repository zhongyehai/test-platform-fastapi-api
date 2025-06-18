import json
import uuid

from fastapi import Request, Response


async def set_body(request: Request, body: bytes):
    async def receive():
        return {"type": "http.request", "body": body}

    request._receive = receive


async def get_body(request: Request) -> str:
    """ 获取请求body """
    body = await request.body()
    await set_body(request, body)
    return body.decode()


def register_request_hook(app):
    @app.middleware("http")
    async def before_request(request: Request, call_next):
        """ 请求前置拦截 """

        # 获取request_id
        request_id = request.headers.get("Request-Id") or str(uuid.uuid4())
        request.app.request_id = request_id
        request.app.request_path = request.url.path

        # 注入日志上下文
        # TODO logger.configure(extra={"request_id": request_id})

        # 获取测试类型
        if "api-test" in request.url.path:
            request.app.test_type = "api"
        elif "app-test" in request.url.path:
            request.app.test_type = "app"
        elif "ui-test" in request.url.path:
            request.app.test_type = "ui"

        # 非文件上传接口，获取请求体并记录日志
        is_upload_file = request.headers.get("content-type", "").startswith("multipart/form-data")
        request.state.is_upload_file = is_upload_file
        if not is_upload_file:
            # 把解析后的body保存在state对象上，方便在出错的时候保存请求数据
            await set_body(request, await request.body())
            request.state.set_body = await get_body(request)
            request.app.logger.info(
                f'【{request.method}】【{request_id}】【{request.url.path}】: {request.query_params or request.state.set_body}')

        response: Response = await call_next(request)

        # 打印响应
        if 'download' not in request.url.path and '/report/step-img' not in request.url.path and '/report/suite-list' not in request.url.path:
            response_body = b"".join([chunk async for chunk in response.body_iterator])
            request.app.logger.info(
                f'【{request.method}】【{request_id}】【{request.url.path}】: {json.loads(response_body.decode())}')

            # 重建响应迭代器
            async def new_body_iterator():
                yield response_body

            response.body_iterator = new_body_iterator()
        return format_response(response, request)


def format_response(response, request: Request):
    """ 格式化响应信息 """
    match response.status_code:
        case 401:
            return request.app.not_login()
        case 404:
            return request.app.url_not_find()
        case 405:
            return request.app.method_not_allowed()
        case _:
            return response
