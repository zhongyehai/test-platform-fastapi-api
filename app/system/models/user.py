# -*- coding: utf-8 -*-
import datetime

import jwt
import hashlib

from app.baseModel import BaseModel, fields, pydantic_model_creator
from app.enums import DataStatusEnum


class Permission(BaseModel):
    """ 权限表 """

    num = fields.IntField(null=True, default=0, description="序号")
    name = fields.CharField(30, default='', description="权限名称")
    desc = fields.CharField(256, null=True, default='', description="权限备注")
    source_addr = fields.CharField(256, default='', description="权限路径")
    source_type = fields.CharField(256, default="api", description="权限类型， front前端, api后端")
    source_class = fields.CharField(256, default="api",
                                    description="权限分类, source_type为front时, menu菜单, button按钮;  source_type为api时, 为请求方法")

    class Meta:
        table = "system_permission"
        table_description = "权限表"


class Role(BaseModel):
    """ 角色表 """

    name = fields.CharField(30, default='', description="角色名称")
    extend_role = fields.JSONField(default=[], description="继承其他角色的权限")
    desc = fields.CharField(256, null=True, default='', description="权限备注")

    class Meta:
        table = "system_role"
        table_description = "角色表"

    async def insert_role_permissions(self, id_list: list):
        """ 批量插入角色权限映射 """
        await RolePermissions.bulk_create([RolePermissions(role_id=self.id, permission_id=p_id) for p_id in id_list])

    async def delete_role_permissions(self):
        """ 批量删除角色权限映射 """
        await RolePermissions.filter(role_id=self.id).delete()

    async def update_role_permissions(self, permission_id_list):
        """ 更新角色权限映射 """
        await self.delete_role_permissions()
        await self.insert_role_permissions(permission_id_list)

    @classmethod
    async def get_user_role_list(cls, user_id):
        """ 获取用户的角色id list """
        user_roles = await UserRoles.filter(user_id=user_id).all().values("role_id")
        return [user_role["role_id"] for user_role in user_roles]

    @classmethod
    async def get_extend_role(cls, role_id, id_list=[]):
        """ 获取当前角色继承的角色 """
        id_list.append(role_id)
        role = await Role.get(id=role_id)
        for extend_role_id in role.extend_role:
            await cls.get_extend_role(extend_role_id, id_list)
        return id_list


class RolePermissions(BaseModel):
    """ 角色权限映射表 """

    role_id = fields.IntField(description="角色id")
    permission_id = fields.IntField(description="权限id")

    class Meta:
        table = "system_role_permissions"
        table_description = "角色权限映射表"


class User(BaseModel):
    """ 用户表 """

    account = fields.CharField(50, index=True, default='', description="账号")
    password = fields.CharField(128, default='', description="密码")
    name = fields.CharField(12, default='', description="姓名")
    status = fields.CharEnumField(DataStatusEnum, default=DataStatusEnum.ENABLE, description="状态，enable/disable")
    business_list = fields.JSONField(default=[], description="用户所在的业务线")
    last_update_password_time = fields.DatetimeField(auto_now_add=True, description="最近一次修改密码时间")

    class Meta:
        table = "system_user"
        table_description = "用户表"

    def make_token(self, api_permissions, time_out, secret_key: str):
        """ 生成token """
        user_info = {
            "id": self.id,
            "account": self.account,
            "name": self.name,
            "business_list": self.business_list,
            "api_permissions": api_permissions,
            "exp": datetime.datetime.now().timestamp() + time_out
        }
        return jwt.encode(user_info, secret_key)

    @classmethod
    def check_token(cls, token: str, secret_key: str):
        """ 解析token """
        try:
            return jwt.decode(token, secret_key, algorithms=["HS256"])
        except jwt.exceptions.InvalidTokenError:
            return False

    @classmethod
    def password_to_hash(cls, password, secret_key):
        """ h密码转hash值 """
        password_and_secret_key = password + secret_key
        hash_obj = hashlib.md5(password_and_secret_key.encode('utf-8'))  # 使用md5函数进行加密
        return hash_obj.hexdigest()  # 转换为16进制

    def verify_password(self, password, secret_key):
        """ 校验密码 """
        input_password = self.password_to_hash(password, secret_key)
        return input_password == self.password

    async def insert_user_roles(self, id_list):
        """ 插入用户角色映射 """
        await UserRoles.bulk_create([UserRoles(user_id=self.id, role_id=r_id) for r_id in id_list])

    async def delete_user_roles(self):
        """ 删除用户角色映射 """
        await UserRoles.filter(user_id=self.id).delete()

    async def update_user_roles(self, role_id_list):
        """ 更新用户角色映射 """
        await self.delete_user_roles()
        await self.insert_user_roles(role_id_list)

    async def get_role_id(self, role_id: []):
        """ 获取角色的所有权限id """
        role_id_list, all_permission_id_list = [], []
        # 获取用户所有的角色id（包括继承的）
        for role_id in await Role.get_user_role_list(self.id):
            role_list = []
            await Role.get_extend_role(role_id, role_list)
            role_id_list.extend(role_list)

    @classmethod
    async def get_all_permission_id_list(cls, role_id_list: []):
        """ 获取角色的所有权限id """
        permission_id_list = await RolePermissions.filter(role_id__in=role_id_list).all().values("permission_id")
        return [permission_id["permission_id"] for permission_id in permission_id_list]

    @classmethod
    async def get_role_permissions(cls, role_id_list):
        """ 根据角色列表，获取权限信息 """
        permission_id_list = await cls.get_all_permission_id_list(role_id_list)
        all_permissions = await Permission.filter(id__in=permission_id_list).all().values("id")
        all_list = [permissions["id"] for permissions in all_permissions]
        front_list = await cls.get_permissions_by_filed(permission_id_list, "front", "id")
        api_list = await cls.get_permissions_by_filed(permission_id_list, "api", "id")
        return {
            "all_permissions": all_list,
            "api_permission": api_list,
            "front_permission": front_list
        }

    @classmethod
    async def get_permissions_by_filed(cls, permission_id_list, source_type, filed=None):
        """ 根据权限获取指定字段 """
        data_list = await Permission.filter(id__in=permission_id_list, source_type=source_type).all().values(filed)
        return list({data[filed] for data in data_list})

    async def get_user_permissions(self):
        """ 获取用户的前端权限 """
        role_id_list = []
        # 获取用户所有的角色id（包括继承的）
        for role_id in await Role.get_user_role_list(self.id):
            role_list = []
            await Role.get_extend_role(role_id, role_list)
            role_id_list.extend(role_list)
        role_id_list = list(set(role_id_list))

        # 获取用户拥有的角色的所有权限id
        all_permission_id_list = await self.get_all_permission_id_list(role_id_list)
        front_source_addr_list = await self.get_permissions_by_filed(all_permission_id_list, "front", "source_addr")
        api_source_addr_list = await self.get_permissions_by_filed(all_permission_id_list, "api", "source_addr")

        return {
            "front_addr_list": front_source_addr_list,
            "api_addr_list": api_source_addr_list,
        }


class UserRoles(BaseModel):
    """ 用户角色映射表 """

    user_id = fields.IntField(description="用户id")
    role_id = fields.IntField(description="角色id")

    class Meta:
        table = "system_user_roles"
        table_description = "用户角色映射表"


PermissionPydantic = pydantic_model_creator(Permission, name="Permission")
RolePydantic = pydantic_model_creator(Role, name="Role")
RolePermissionsPydantic = pydantic_model_creator(RolePermissions, name="RolePermissions")
UserPydantic = pydantic_model_creator(User, name="User", exclude=("password",))  # 不返回密码相关内容
UserRolesPydantic = pydantic_model_creator(UserRoles, name="UserRoles")
