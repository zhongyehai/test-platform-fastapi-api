from typing import List
from fastapi import Request

from ..routers import config_router
from app.config.model_factory import BusinessLine, BusinessLinePydantic
from ..forms.business import FindBusinessLineForm, GetBusinessForm, BusinessToUserForm, PostBusinessForm, \
    PutBusinessForm, DeleteBusinessForm
from ...system.models.user import User


@config_router.login_post("/business/list", response_model=List[BusinessLinePydantic], summary="业务线列表")
async def get_business_list(form: FindBusinessLineForm, request: Request):
    query_data = await form.make_pagination(BusinessLine, user=request.state.user)
    return request.app.get_success(data=query_data)


@config_router.login_put("/business/user", summary="批量绑定/解除绑定业务线与用户的关系")
async def batch_to_user(form: BusinessToUserForm, request: Request):
    await BusinessLine.business_to_user(form.business_list, form.user_list, form.command)
    return request.app.put_success()


@config_router.login_post("/business/detail", summary="获取业务线详情")
async def get_business_detail(form: GetBusinessForm, request: Request):
    business = await form.validate_request(request)
    return request.app.get_success(business)


@config_router.login_post("/business", summary="新增业务线")
async def add_business(form: PostBusinessForm, request: Request):
    await form.validate_request(request)
    business = await BusinessLine.model_create(form.dict(), request.state.user)

    # 给创建者添加绑定关系
    request.state.user.business_list.append(business.id)
    await User.filter(id=request.state.user.id).update(business_list=request.state.user.business_list)

    # 重新生成token
    user = await User.filter(id=request.state.user.id).first()
    token = user.make_token(
        request.state.user.api_permissions, request.app.conf.token_time_out, request.app.conf.token_secret_key)
    return request.app.post_success(data={"token": token, "business_id": user.business_list})


@config_router.login_put("/business", summary="修改业务线")
async def change_business(form: PutBusinessForm, request: Request):
    business = await form.validate_request(request)
    await business.model_update(form.dict(), request.state.user)
    return request.app.put_success()


@config_router.login_delete("/business", summary="删除业务线")
async def delete_business(form: DeleteBusinessForm, request: Request):
    business = await form.validate_request(request)
    await business.model_delete()
    return request.app.delete_success()
