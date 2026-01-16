import httpx
from fastapi import Request, Depends

from ...models.system.model_factory import User, Role, UserRoles
from ...models.config.model_factory import BusinessLine
from ...schemas.system import sso as schema
from utils.parse.parse_token import parse_token


async def get_sso_server_info(request: Request):
    """ 获取sso相关信息 """
    async with httpx.AsyncClient(verify=False) as client:
        response = await client.post(url=f'{request.app.conf.SSO.HOST}/.well-known/openid-configuration', timeout=30)
    res = response.json()
    return {
        "authorization_endpoint": res["authorization_endpoint"], "token_endpoint": res["token_endpoint"],
        "userinfo_endpoint": res["userinfo_endpoint"], "jwks_uri": res["jwks_uri"]
    }


async def get_sso_token(request: Request, code):
    """ 从sso服务器获取用户token """
    sso = request.app.conf.SSO
    url = f'{sso.HOST}{sso.SSO_TOKEN_ENDPOINT}'
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": sso.CLIENT_ID,
        "client_secret": sso.CLIENT_SECRET,
        "redirect_uri": sso.REDIRECT_URI
    }
    request.app.logger.info(f'get_sso_token: \nurl: {url}, \ndata: {data}')
    async with httpx.AsyncClient(verify=False) as client:
        response = await client.post(url=url, data=data)
    request.app.logger.info(f'get_sso_token.res.text: \n{response.text}')
    return response.json()


async def get_sso_redirect_uri(request: Request):
    """ 返回重定向的登录地址 """
    redirect_addr = request.app.conf.SSO.FRONT_REDIRECT_ADDR if request.app.conf.AuthInfo.AUTH_TYPE == "SSO" else None
    return request.app.not_login(redirect_addr)



async def login_by_sso_code(request: Request, form: schema.GetSsoTokenForm = Depends()):

    # 根据接收到的code，获取token
    sso_token = await get_sso_token(request, form.code)

    # 解析token
    payload = parse_token(sso_token["id_token"])["payload"]
    sso_user_id, sso_user_name = payload.get("sub"), payload.get("user_name")
    phone_number, email = payload.get("phoneNumber"), payload.get("email")

    # user = User.query.filter_by(sso_user_id=sso_user_id, name=sso_user_name).first()
    user = await User.filter(sso_user_id=sso_user_id, name=sso_user_name).first()
    if not user:  # 数据库中没有这个用户，需插入一条数据，再生成token
        user = await User.filter(sso_user_id=None, name=sso_user_name).first()
        if user:
            await user.model_update({"sso_user_id": sso_user_id, "email": email, "phone_number": phone_number})
        else:
            # 新增用户，默认为公共业务线权限
            common_id = await BusinessLine.filter(code="common").first().values("id")
            user = await User.model_create({
                "sso_user_id": sso_user_id,
                "name": sso_user_name,
                "phone_number": phone_number,
                "email": email,
                "business_list": [common_id["id"]],
                "password": "123456"
            })

            # 角色为测试人员
            role_id = await Role.filter(name="测试人员").first().values("id")
            await UserRoles.model_create({"user_id": user.id, "role_id": role_id["id"]})
    else:  # 历史数据，如果没有手机号，需要更新一下
        if user.phone_number is None:
            await user.model_update({"email": email, "phone_number": phone_number})

    # 根据用户id信息生成token，并返回给前端
    user_info = await user.build_access_token(
        request.app.conf.AuthInfo.ACCESS_TOKEN_TIME_OUT,
        request.app.conf.AuthInfo.SECRET_KEY
    )
    user_info["refresh_token"] = user.make_refresh_token(
        request.app.conf.AuthInfo.ACCESS_TOKEN_TIME_OUT,
        request.app.conf.AuthInfo.SECRET_KEY
    )
    return request.app.success("登录成功", user_info)
