import json
import os

from fastapi import Request

from ..routers import tool


@tool.post("/examination", summary="获取征信从业资格考试题目")
async def api_examination(request: Request):
    with open(os.path.join(os.path.dirname(__file__), "../zhengXinTest.json"), encoding="utf8") as file:
        zheng_xin_test_data = json.load(file)
    return request.app.get_success(data=zheng_xin_test_data)
