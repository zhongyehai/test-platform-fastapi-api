# -*- coding: utf-8 -*-
from typing import Optional
from pydantic import Field
from fastapi import Request

from ...baseForm import BaseForm, PaginationForm
from ..model_factory import User, UserPydantic
from ...enums import DataStatusEnum


class CreateUserForm(BaseForm):
    """ 创建用户的验证 """
    user_list: list = Field(..., title="要创建的用户列表")

    async def validate_request(self, *args, **kwargs):
        """ 校验用户数据 """
        name_list, account_list = [], []

        name_max_length = User.filed_max_length("name")
        account_max_length = User.filed_max_length("account")
        password_max_length = User.filed_max_length("password")

        for index, user in enumerate(self.user_list):
            name, account, password = user.get("name"), user.get("account"), user.get("password")
            business_list, role_list = user.get("business_list"), user.get("role_list")

            if not all((name, account, password, business_list, role_list)):
                raise ValueError(f'第【{index + 1}】行，数据需填完')

            self.validate_is_true(
                3 < len(password) < password_max_length,
                msg=f'第【{index + 1}】行，密码长度长度为4~{password_max_length}位'
            )

            if name in name_list:
                raise ValueError(f'第【{index + 1}】行，与第【{name_list.index(name) + 1}】行，用户名重复')

            self.validate_is_true(
                1 < len(name) < name_max_length,
                msg=f'第【{index + 1}】行，用户名长度长度为2~{name_max_length}位')

            await self.validate_data_is_not_exist(f'【第{index + 1}】行，用户名【{name}】已存在', User, name=name)

            if account in account_list:
                raise ValueError(f'第【{index + 1}】行，与第【{account_list.index(account) + 1}】行，账号重复')

            self.validate_is_true(
                1 < len(account) < account_max_length,
                f'第【{index + 1}】行，账号长度长度为2~{account_max_length}位'
            )

            await self.validate_data_is_not_exist(f'第【{index + 1}】行，账号【{account}】已存在', User, account=account)
            name_list.append(name)
            account_list.append(account)


class ChangePasswordForm(BaseForm):
    """ 修改密码的校验 """
    old_password: str = Field(..., title="旧密码", min_length=4, max_length=User.filed_max_length("password"))
    new_password: str = Field(..., title="新密码", min_length=4, max_length=User.filed_max_length("password"))
    sure_password: str = Field(..., title="确认密码", min_length=4, max_length=User.filed_max_length("password"))

    async def validate_request(self, request: Request, *args, **kwargs):
        password_max_length = User.filed_max_length("password")
        self.validate_is_true(self.new_password == self.sure_password, msg='新密码与确认密码不一致')
        for password in [self.old_password, self.new_password, self.sure_password]:
            self.validate_is_true(3 < len(password) < password_max_length, msg=f'密码长度为4~{password_max_length}位')
        user = await User.filter(id=request.state.user.id).first()
        self.validate_is_true(user.verify_password(self.old_password, request.app.conf.hash_secret_key),
                              "账号或密码错误")


class MigrateUserChangePasswordForm(BaseForm):
    """ 迁移用户修改密码的校验，拿不到旧密码，所以不校验旧密码是否正确 """
    account: str = Field(..., title="账号")
    old_password: str = Field(..., title="旧密码", min_length=4, max_length=User.filed_max_length("password"))
    new_password: str = Field(..., title="新密码", min_length=4, max_length=User.filed_max_length("password"))
    sure_password: str = Field(..., title="确认密码", min_length=4, max_length=User.filed_max_length("password"))

    async def validate_request(self, request: Request, *args, **kwargs):
        user = await self.validate_data_is_exist("账号或密码错误", User, account=self.account)  # 账号存在
        if user.need_change_password != 1:  # 从老版本迁移过来的数据已经改过密码的，不允许用此渠道
            raise ValueError("请重用户设置处修改密码")

        password_max_length = User.filed_max_length("password")
        self.validate_is_true(self.new_password == self.sure_password, msg='新密码与确认密码不一致')
        for password in [self.old_password, self.new_password, self.sure_password]:
            self.validate_is_true(3 < len(password) < password_max_length, msg=f'密码长度为4~{password_max_length}位')
        return user


class LoginForm(BaseForm):
    """ 登录校验 """
    account: str = Field(..., title="账号", min_length=4, max_length=User.filed_max_length("account"))
    password: str = Field(..., title="密码", min_length=4, max_length=User.filed_max_length("password"))

    async def validate_request(self, request: Request, *args, **kwargs):
        user = await self.validate_data_is_exist("账号或密码错误", User, account=self.account)  # 账号存在
        if user.need_change_password == 1: raise ValueError("需要修改密码")  # 从老版本迁移过来的数据还没改过密码的，强制改密码
        self.validate_is_true(user.verify_password(self.password, request.app.conf.hash_secret_key), "账号或密码错误")
        self.validate_is_true(user.status != DataStatusEnum.DISABLE, "账号为冻结状态，请联系管理员")
        return user


class FindUserForm(PaginationForm):
    """ 查找用户参数校验 """
    name: Optional[str] = Field(title="用户名")
    account: Optional[str] = Field(title="账号")
    detail: Optional[str] = Field(title="是否获取用户详情")
    status: Optional[DataStatusEnum] = Field(title="状态")
    role_id: Optional[int] = Field(title="角色id")

    async def validate_request(self, request: Request, *args, **kwargs):
        if self.detail:
            self.validate_is_true(
                User.has_api_permissions(request.state.user.api_permissions, request.url.path),
                "当前角色无权限获取用户详情")

        # 非管理员，只能获取到当前用户有的业务线的人
        request.state.user_list = []
        if User.is_not_admin(request.state.user.api_permissions):
            user_list = set()
            for business_id in request.state.user.business_list:
                users = await User.filter(business_list__contains=business_id, id__not_in=user_list).all().values("id")
                user_list = user_list.union({user["id"] for user in users})
            request.state.user_list = list(user_list)

    def get_query_filter(self, *args, **kwargs):
        """ 查询条件 """
        user_list, filter_dict = kwargs.get("user_list"), {}

        if user_list:
            filter_dict["id__in"] = user_list
        if self.name:
            filter_dict["name__icontains"] = self.name
        if self.account:
            filter_dict["account"] = self.account
        if self.status:
            filter_dict["status"] = self.status
        if self.role_id:
            filter_dict["role_id"] = self.role_id
        return filter_dict


class GetUserForm(BaseForm):
    """ 获取用户信息 """

    id: int = Field(..., title="用户id")

    async def validate_user_is_exist(self):
        return await self.validate_data_is_exist(f"用户不存在", User, id=self.id)

    async def validate_request(self, request: Request, *args, **kwargs):
        return await self.validate_user_is_exist()


class DeleteUserForm(GetUserForm):
    """ 删除用户 """

    async def validate_request(self, request: Request, *args, **kwargs):
        user = await self.validate_user_is_exist()
        self.validate_is_true(request.state.user.id != self.user_id, "不能自己删自己")
        return user


class ChangeStatusUserForm(GetUserForm):
    """ 改变用户状态 """


class EditUserForm(GetUserForm):
    """ 编辑用户的校验 """
    name: str = Field(..., title="用户名", min_length=2, max_length=User.filed_max_length("name"))
    account: str = Field(..., title="账号", min_length=2, max_length=User.filed_max_length("account"))
    business_list: list = Field(..., title="业务线")
    role_list: list = Field(..., title="角色")
    password: Optional[str] = Field(title="用户密码，如果有，则可直接修改密码")

    async def validate_request(self, request: Request, *args, **kwargs):
        name_max_length = User.filed_max_length("name")
        self.validate_is_true(1 < len(self.name) < name_max_length, msg=f'用户名长度为2~{name_max_length}位')

        account_max_length = User.filed_max_length("account")
        self.validate_is_true(1 < len(self.account) < account_max_length, msg=f'账号长度为2~{account_max_length}位')

        if self.password:
            password_max_length = User.filed_max_length("password")
            self.validate_is_true(1 < len(self.password) < password_max_length,
                                  msg=f'密码长度为2~{password_max_length}位')
            self.password = User.password_to_hash(self.password, request.app.conf.hash_secret_key)

        return await self.validate_user_is_exist()
