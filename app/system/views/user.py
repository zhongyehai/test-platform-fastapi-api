import datetime
from typing import List
from fastapi import Request

from app.system.routers import system_router
from app.system.model_factory import User, UserPydantic, Role
from app.system.forms.user import (
    CreateUserForm, EditUserForm, ChangePasswordForm, LoginForm, FindUserForm, GetUserForm, ChangeStatusUserForm,
    MigrateUserChangePasswordForm
)


@system_router.login_post("/user/list", response_model=List[UserPydantic], summary="获取用户列表")
async def get_user_list(form: FindUserForm, request: Request):
    await form.validate_request(request)
    get_filed = [] if form.detail else ["id", "name"]
    query_data = await form.make_pagination(
        User, get_filed=get_filed, user_list=request.state.user_list, not_get_filed=['password'])
    return request.app.get_success(data=query_data)


@system_router.admin_post("/user/detail", summary="获取用户详情")
async def get_user_detail(form: GetUserForm, request: Request):
    user = await form.validate_request(request)
    return request.app.get_success(user)


@system_router.permission_post("/user", summary="新增用户")
async def add_user(form: CreateUserForm, request: Request):
    await form.validate_request(request)
    for user_dict in form.user_list:
        user_dict["password"] = User.password_to_hash(user_dict["password"], request.app.conf.hash_secret_key)
        user = await User.model_create(user_dict, request.state.user)
        await user.insert_user_roles(user_dict["role_list"])
    return request.app.post_success()


@system_router.permission_put("/user", summary="修改用户")
async def change_user(form: EditUserForm, request: Request):
    user = await form.validate_request(request)
    data = form.dict()
    role_list = data.pop("role_list")
    await user.model_update(data, request.state.user)
    await user.update_user_roles(role_list)
    return request.app.put_success()


# @system_router.admin_delete("/user", summary="删除用户")
# async def delete_user(form: DeleteUserForm, request: Request):
#     user = await form.validate_request(request)
#     await request.data.delete_user_roles()
#     await User.delete_data(id=form.id)
#     return request.app.delete_success()


@system_router.post("/user/login", summary="用户登录")
async def user_login(form: LoginForm, request: Request):
    user = await form.validate_request(request)
    permissions = await user.get_user_permissions()
    front_addr_list, api_addr_list = permissions["front_addr_list"], permissions["api_addr_list"]

    user_info = {
        "id": user.id,
        "account": user.account,
        "name": user.name,
        "business_list": user.business_list,
        "front_permissions": front_addr_list
    }
    token = user.make_token(api_addr_list, request.app.conf.token_time_out, request.app.conf.token_secret_key)
    user_info["token"] = token
    return request.app.success("登录成功", user_info)


@system_router.admin_post("/user/logout", summary="用户登出")
async def user_logout(request: Request):
    return request.app.success(msg="登出成功")


@system_router.permission_post("/user/role", summary="获取用户的角色列表")
async def get_user_role_list(form: GetUserForm, request: Request):
    await form.validate_request(request)
    role_list = await Role.get_user_role_list(form.id)
    return request.app.get_success(role_list)


@system_router.permission_put("/user/status", summary="修改用户状态")
async def change_user_status(form: ChangeStatusUserForm, request: Request):
    user = await form.validate_request(request)
    await user.model_update({"status": 1 if user.status == 0 else 0}, request.state.user)
    return request.app.put_success()


@system_router.login_put("/user/password", summary="修改密码")
async def change_user_password(form: ChangePasswordForm, request: Request):
    await form.validate_request(request)
    new_password = User.password_to_hash(form.new_password, request.app.conf.hash_secret_key)
    await User.filter(id=request.state.user.id).update(password=new_password, need_change_password=0)
    return request.app.put_success()


@system_router.put("/user/password/migrate", summary="迁移用户修改密码")
async def migrate_user_change_password(form: MigrateUserChangePasswordForm, request: Request):
    user = await form.validate_request(request)
    new_password = User.password_to_hash(form.new_password, request.app.conf.hash_secret_key)
    await User.filter(id=user.id).update(password=new_password, need_change_password=0)
    return request.app.put_success()
