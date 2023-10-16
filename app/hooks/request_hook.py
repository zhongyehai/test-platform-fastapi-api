from loguru import logger
from fastapi import Request, Response

from app.baseForm import CurrentUserModel
from utils.view import restful
from ..enums import AuthType
from utils.util.file_util import LOG_ADDRESS
from utils.log import logger


# logger.add(
#     f"{LOG_ADDRESS}" + "/{time}.log",
#     rotation='00:00',  # 每天0点新建文件继续记录
#     retention='10 days',  # 10天一清理
#     format="{time:YYYY-MM-DD HH:mm:ss.ms} {process}-{thread} [{extra[request_id]}] | {level} | {module}.{function}:{line} : {message}"
# )


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
        request_id = request.headers.get("Request-Id")
        request.app.request_id = request_id
        request.app.request_path = request.url.path

        # 身份验证
        if msg := check_login_and_permissions(app.url_required_map, request):
            return msg

        # 非文件上传接口，获取请求体并记录日志
        if request.url.path.endswith("upload") is False:
            await set_body(request, await request.body())
            request.state.set_body = await get_body(request)  # 把解析后的body保存在state对象上，方便在出错的时候保存请求数据

        if request.url.path.endswith("/api/job/queue") is False:
            logger.info(
                f'【{request.state.user.name}】【{request.method}】【{request_id}】【{request.url}】: \n请求参数：{"" if request.url.path.endswith("upload") else request.state.set_body}')

        response: Response = await call_next(request)

        return format_response(response)


def parse_request_path(request: Request):
    """ /api/apiTest/project/detail  =>  /project/detail 方便去拿接口和身份验证的映射"""
    request_path = request.url.path.split('/')
    return f'/{"/".join(request_path[3:])}'


def check_login_and_permissions(url_required_map, request):
    """ 身份验证 """
    request.state.user = CurrentUserModel(id=None, account="", name="", business_list=[], api_permissions=[])

    # 访问的是swagger的内容，不校验身份
    if request.url.path in [request.app.docs_url, request.app.redoc_url, "/docs", "/redoc", request.app.openapi_url]:
        return

    # 解析用户信息
    from ..system.model_factory import User
    if user := User.check_token(request.headers.get("x-token", ""), request.app.conf.token_secret_key):
        request.state.user = CurrentUserModel(**user)
    is_not_admin = User.is_not_admin(request.state.user.api_permissions)

    # 身份验证
    auth_type = url_required_map.get(parse_request_path(request))  # 根据请求路径判断是否需要身份验证
    match auth_type:
        case AuthType.login:
            if not user: return restful.not_login()
        case AuthType.permission:
            if is_not_admin and request.url.path not in request.state.user.api_permissions: return restful.forbidden()
        case AuthType.admin:
            if is_not_admin: return restful.forbidden()


def format_response(response):
    """ 格式化响应信息 """
    match response.status_code:
        case 404:
            return restful.url_not_find()
        case 405:
            return restful.method_not_allowed()
        case _:
            return response
