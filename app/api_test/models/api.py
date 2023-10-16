from ...baseModel import BaseApi, fields, pydantic_model_creator
from ...enums import ApiLevelEnum, ApiMethodEnum, DataStatusEnum, ApiBodyTypeEnum


class ApiMsg(BaseApi):
    """ 接口表 """

    time_out = fields.IntField(default=60, null=True, description="request超时时间，默认60秒")
    addr = fields.CharField(255, null=True, description="接口地址")
    up_func = fields.JSONField(default=[], description="接口执行前的函数")
    down_func = fields.JSONField(default=[], description="接口执行后的函数")
    method = fields.CharEnumField(ApiMethodEnum, default=ApiMethodEnum.GET, description="请求方式")
    level = fields.CharEnumField(ApiLevelEnum, default=ApiLevelEnum.P1, description="接口重要程度：P0、P1、P2")
    headers = fields.JSONField(default=[{"key": None, "value": None, "remark": None}], description="头部信息")
    params = fields.JSONField(default=[{"key": None, "value": None, "remark": None}], description="url参数")
    body_type = fields.CharEnumField(ApiBodyTypeEnum, default=ApiBodyTypeEnum.JSON, description="请求体数据类型，json/form/text/urlencoded")
    data_form = fields.JSONField(
        default=[{"data_type": None, "key": None, "remark": None, "value": None}], description="form-data参数")
    data_urlencoded = fields.JSONField(default={}, description="form_urlencoded参数")
    data_json = fields.JSONField(default={}, description="json参数")
    data_text = fields.TextField(null=True, default=None, description="文本参数")
    response = fields.JSONField(default={}, description="响应对象")
    extracts = fields.JSONField(
        default=[
            {"status": 1, "key": None, "data_source": None, "value": None, "remark": None, "update_to_header": None}],
        description="提取信息"
    )
    validates = fields.JSONField(
        default=[{"status": 1, "key": None, "value": None, "remark": None, "data_type": None, "data_source": None,
                  "validate_type": "data", "validate_method": None}],
        description="断言信息")
    status = fields.CharEnumField(DataStatusEnum, default=DataStatusEnum.ENABLE, description="此接口状态，对应swagger的废弃状态, enable/disable")
    quote_count = fields.IntField(default=0, description="被引用次数，即多少个步骤直接使用了此接口")

    class Meta:
        table = "api_test_api"
        table_description = "接口测试接口信息表"

    async def add_quote_count(self):
        """ 被引用次数+1 """
        self.quote_count = 1 if self.quote_count is None else self.quote_count + 1
        await self.__class__.filter(id=self.id).update(quote_count=self.quote_count)

    async def subtract_quote_count(self):
        """ 被引用次数-1 """
        self.quote_count = 0 if not self.quote_count else self.quote_count - 1
        await self.__class__.filter(id=self.id).update(quote_count=self.quote_count)

    @classmethod
    def make_pagination(cls, form):
        """ 解析分页条件 """
        filters = []
        if form.moduleId.data:
            filters.append(ApiMsg.module_id == form.moduleId.data)
        if form.name.data:
            filters.append(ApiMsg.name.like(f"%{form.name.data}%"))
        return cls.pagination(
            page_num=form.pageNum.data,
            page_size=form.pageSize.data,
            filters=filters,
            order_by=ApiMsg.num.asc()
        )


ApiMsgPydantic = pydantic_model_creator(ApiMsg, name="ApiMsg")
