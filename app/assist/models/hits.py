# -*- coding: utf-8 -*-
from datetime import datetime

from app.baseModel import BaseModel, fields, pydantic_model_creator


class Hits(BaseModel):
    """ 自动化测试触发的问题记录 """

    date = fields.CharField(128, default=datetime.now, description="问题触发日期")
    hit_type = fields.CharField(128, default="", description="问题类型")
    hit_detail = fields.TextField(default="", description="问题内容")
    test_type = fields.CharField(8, default="", description="测试类型，接口、appUi、webUi")
    project_id = fields.IntField(index=True, description="服务id")
    report_id = fields.IntField(index=True, description="测试报告id")
    env = fields.CharField(128, index=True, description="运行环境")
    desc = fields.TextField(default="", description="备注")

    class Meta:
        table = "auto_test_hits"
        table_description = "自动化测试触发问题记录"

    @classmethod
    def make_pagination(cls, form):
        """ 解析分页条件 """
        filters = []
        if form.date.data:
            filters.append(cls.date == form.date.data)
        if form.report_id.data:
            filters.append(cls.report_id == form.report_id.data)
        if form.hit_type.data:
            filters.append(cls.hit_type == form.hit_type.data)
        if form.test_type.data:
            filters.append(cls.test_type == form.test_type.data)
        return cls.pagination(
            page_num=form.pageNum.data,
            page_size=form.pageSize.data,
            filters=filters,
            order_by=cls.id.desc()
        )


HitsPydantic = pydantic_model_creator(Hits, name="Hits")
