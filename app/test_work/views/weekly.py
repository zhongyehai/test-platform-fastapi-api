import os.path
from typing import List
from fastapi import Request
from fastapi.responses import FileResponse

from ..routers import test_work
from ..model_factory import WeeklyConfigModel, WeeklyModel, WeeklyConfigModelPydantic, WeeklyModelPydantic
from ..forms.weekly import (
    GetWeeklyConfigListForm, GetWeeklyConfigForm, AddWeeklyConfigForm, ChangeWeeklyConfigForm, DeleteWeeklyConfigForm,
    GetWeeklyListForm, GetWeeklyForm, AddWeeklyForm, ChangeWeeklyForm, DeleteWeeklyForm, DownloadWeeklyForm
)
from ...system.model_factory import User
from utils.util.file_util import TEMP_FILE_ADDRESS
from utils.make_data.make_weekly import make_weekly_excel, make_current_weekly_excel


@test_work.post("/weekly/config/list", response_model=List[WeeklyConfigModelPydantic], summary="获取产品、项目列表")
async def get_weekly_config_list(form: GetWeeklyConfigListForm, request: Request):
    query_data = await form.make_pagination(WeeklyConfigModel, user=request.state.user)
    return request.app.get_success(data=query_data)


@test_work.login_post("/weekly/config/detail", summary="获取产品、项目详情")
async def get_weekly_config_detail(form: GetWeeklyConfigForm, request: Request):
    weekly_config = await form.validate_request(request)
    return request.app.get_success(data=weekly_config)


@test_work.login_post("/weekly/config", summary="新增产品、项目")
async def add_weekly_config(form: AddWeeklyConfigForm, request: Request):
    await form.validate_request(request)
    await WeeklyConfigModel.model_create(form.dict(), request.state.user)
    return request.app.post_success()


@test_work.login_put("/weekly/config", summary="修改产品、项目")
async def change_weekly_config(form: ChangeWeeklyConfigForm, request: Request):
    weekly_config = await form.validate_request(request)
    await weekly_config.model_update(form.dict(), request.state.user)
    return request.app.put_success()


@test_work.login_delete("/weekly/config", summary="删除产品、项目")
async def delete_weekly_config(form: DeleteWeeklyConfigForm, request: Request):
    weekly_config = await form.validate_request(request)
    await weekly_config.model_delete()
    return request.app.delete_success()


@test_work.login_post("/weekly/list", response_model=List[WeeklyModelPydantic], summary="获取周报列表")
async def get_weekly_list(form: GetWeeklyListForm, request: Request):
    query_data = await form.make_pagination(WeeklyModel, user=request.state.user)
    return request.app.get_success(data=query_data)


@test_work.login_post("/weekly/download", summary="导出周报")
async def download_weekly_(form: DownloadWeeklyForm, request: Request):
    await form.validate_request()
    # 获取产品、项目数据
    product_dict = await WeeklyConfigModel.get_data_dict()
    user_dict = {user.id: user.name for user in await User.all()}

    if form.download_type == "current":  # 导出本周周报
        # TODO 根据条件筛选
        data_list = await WeeklyModel.make_pagination(form)
        file_name = make_current_weekly_excel(product_dict, data_list, user_dict)  # 生成excel
    else:  # 导出指定时间段的周报
        data_list = await WeeklyModel.make_pagination(form)
        file_name = make_weekly_excel(data_list, form, user_dict)
    return FileResponse(os.path.join(TEMP_FILE_ADDRESS, file_name))


@test_work.login_post("/weekly/detail", summary="获取周报信息")
async def get_weekly_detail(form: GetWeeklyForm, request: Request):
    weekly = await form.validate_request(request)
    return request.app.get_success(data=weekly)


@test_work.login_post("/weekly", summary="新增周报")
async def add_weekly(form: AddWeeklyForm, request: Request):
    await form.validate_request(request)
    await WeeklyModel.model_create(form.dict(), request.state.user)
    return request.app.post_success()


@test_work.login_put("/weekly", summary="修改周报")
async def change_weekly(form: ChangeWeeklyForm, request: Request):
    weekly = await form.validate_request(request)
    await weekly.model_update(form.dict(), request.state.user)
    return request.app.put_success()


@test_work.login_delete("/weekly", summary="删除周报")
async def delete_weekly(form: DeleteWeeklyForm, request: Request):
    weekly = await form.validate_request(request)
    await weekly.model_delete()
    return request.app.delete_success()
