# -*- coding: utf-8 -*-
from app.baseModel import fields, pydantic_model_creator, BaseModel
from ...enums import ReceiveTypeEnum, BusinessLineBindEnvTypeEnum
from ...system.model_factory import User


class BusinessLine(BaseModel):
    """ 业务线 """

    name = fields.CharField(128, null=True, unique=True, description="业务线名")
    code = fields.CharField(128, null=True, unique=True, description="业务线编码")
    receive_type = fields.CharEnumField(
        ReceiveTypeEnum, default=ReceiveTypeEnum.NOT_RECEIVE,
        description="接收通知类型：not_receive:不接收、we_chat:企业微信、ding_ding:钉钉")
    webhook_list = fields.JSONField(default=[], description="接收该业务线自动化测试阶段统计通知地址")
    env_list = fields.JSONField(default=[], description="业务线能使用的运行环境")
    num = fields.IntField(null=True, description="序号")
    bind_env = fields.CharEnumField(BusinessLineBindEnvTypeEnum, default=BusinessLineBindEnvTypeEnum.HUMAN,
                                    description="绑定环境机制，auto：新增环境时自动绑定，human：新增环境后手动绑定")
    desc = fields.CharField(255, null=True, description="描述")

    class Meta:
        table = "config_business"
        table_description = "业务线配置表"

    @classmethod
    async def get_auto_bind_env_id_list(cls):
        """ 获取设置为自动绑定的业务线 """
        query_res = await cls.filter(bind_env=BusinessLineBindEnvTypeEnum.AUTO).all().values("id")
        return [data["id"] for data in query_res]

    @classmethod
    async def business_to_user(cls, business_id_list, user_id_list, command):
        """ 管理业务线与用户的 绑定/解绑  command: add、delete """
        user_list = await User.filter(id__in=user_id_list).all()
        for user in user_list:
            if command == "add":  # 绑定
                user_business_id_list = list({*business_id_list, *user.business_list})
            else:  # 取消绑定
                user_business_id_list = list(set(user.business_list).difference(set(business_id_list)))
            await user.model_update({"business_list": user_business_id_list})

    @classmethod
    async def get_env_list(cls, business_id):
        """ 根据业务线获取选择的运行环境 """
        business = await cls.filter(id=business_id).first()
        return business.env_list

    @classmethod
    def make_pagination(cls, form):
        """ 解析分页条件 """
        filters = []
        if not form.getAll.data and cls.is_not_admin():  # 如果用户不是管理员权限，则只返回当前用户的业务线
            filters.append(cls.id.in_(g.business_list))
        if form.create_user.data:
            filters.append(cls.create_user == form.create_user.data)
        if form.name.data:
            filters.append(cls.name.like(f'%{form.name.data}%'))
        if form.code.data:
            filters.append(cls.code.like(f'%{form.code.data}%'))
        return cls.pagination(
            page_num=form.pageNum.data,
            page_size=form.pageSize.data,
            filters=filters,
            order_by=cls.id.desc()
        )


BusinessLinePydantic = pydantic_model_creator(BusinessLine, name="BusinessLine")
