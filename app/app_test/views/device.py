from typing import List

import requests
from fastapi import Request

from ..routers import app_test
from ...baseForm import ChangeSortForm
from ..model_factory import (
    AppUiRunServer as Server, AppUiRunServerPydantic as RunServerPydantic,
    AppUiRunPhone as Phone, AppUiRunPhonePydantic as RunPhonePydantic
)
from ..forms.device import (
    AddServerForm, GetServerForm, EditServerForm, GetServerListForm,
    AddPhoneForm, GetPhoneForm, EditPhoneForm, GetPhoneListForm
)


@app_test.post("/device/server/list", response_model=List[RunServerPydantic], summary="获取运行服务器列表")
async def app_get_server_list(form: GetServerListForm, request: Request):
    query_data = await form.make_pagination(Server)
    return request.app.get_success(data=query_data)


@app_test.login_put("/device/server/sort", summary="运行服务器排序")
async def app_change_server_sort(form: ChangeSortForm, request: Request):
    await Server.change_sort(**form.dict(exclude_unset=True))
    return request.app.put_success()


@app_test.login_post("/device/server/copy", summary="复制运行服务器")
async def app_copy_server(form: GetServerForm, request: Request):
    server = await form.validate_request()
    new_server = await server.copy()
    return request.app.success("复制成功", data=new_server)


@app_test.login_post("/device/server/run", summary="连接运行服务器")
async def app_run_server(form: GetServerForm, request: Request):
    server = await form.validate_request()
    try:
        status_code = requests.get(f'http://{server.ip}:{server.port}', timeout=5).status_code
    except Exception as error:
        await server.request_fail()
        return request.app.fail(msg="设置的appium服务器地址不能访问，请检查")
    if status_code > 499:  # 5开头的
        await server.request_fail()
        return request.app.fail(msg=f'设置的appium服务器地址响应状态码为 {status_code}，请检查')
    await server.request_success()
    return request.app.success(msg=f'服务器访问成功，响应为：状态码为 {status_code}')


@app_test.login_post("/device/server/detail", summary="获取运行服务器详情")
async def app_get_server_detail(form: GetServerForm, request: Request):
    server = await form.validate_request(request)
    return request.app.get_success(server)


@app_test.login_post("/device/server", summary="新增运行服务器")
async def app_add_server(form: AddServerForm, request: Request):
    await form.validate_request(request)
    server = await Server.model_create(form.dict(), request.state.user)
    return request.app.post_success(data=server)


@app_test.login_put("/device/server", summary="修改运行服务器")
async def app_change_server(form: EditServerForm, request: Request):
    server = await form.validate_request(request)
    await server.model_update(form.dict(), request.state.user)
    return request.app.put_success()


@app_test.login_delete("/device/server", summary="删除运行服务器")
async def app_delete_server(form: GetServerForm, request: Request):
    server = await form.validate_request(request)
    await server.model_delete()
    return request.app.delete_success()


@app_test.post("/device/phone/list", response_model=List[RunPhonePydantic], summary="获取运行设备列表")
async def app_get_phone_list(form: GetPhoneListForm, request: Request):
    query_data = await form.make_pagination(Phone)
    return request.app.get_success(data=query_data)


@app_test.login_put("/device/phone/sort", summary="运行设备排序")
async def app_change_phone_sort(form: ChangeSortForm, request: Request):
    await Phone.change_sort(**form.dict(exclude_unset=True))
    return request.app.put_success()


@app_test.login_post("/device/phone/copy", summary="复制运行设备")
async def app_copy_phone(form: GetPhoneForm, request: Request):
    phone = await form.validate_request()
    new_phone = await phone.copy()
    return request.app.success("复制成功", data=new_phone)


@app_test.login_post("/device/phone/detail", summary="获取运行设备详情")
async def app_get_phone_detail(form: GetPhoneForm, request: Request):
    phone = await form.validate_request(request)
    return request.app.get_success(phone)


@app_test.login_post("/device/phone", summary="新增运行设备")
async def app_add_phone(form: AddPhoneForm, request: Request):
    await form.validate_request(request)
    phone = await Phone.model_create(form.dict(), request.state.user)
    return request.app.post_success(data=phone)


@app_test.login_put("/device/phone", summary="修改运行设备")
async def app_change_phone(form: EditPhoneForm, request: Request):
    phone = await form.validate_request(request)
    await phone.model_update(form.dict(), request.state.user)
    return request.app.put_success()


@app_test.login_delete("/device/phone", summary="删除运行设备")
async def app_delete_phone(form: GetPhoneForm, request: Request):
    phone = await form.validate_request(request)
    await phone.model_delete()
    return request.app.delete_success()
