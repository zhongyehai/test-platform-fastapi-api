from typing import List
from fastapi import Request

from ..routers import ui_test
from ...baseForm import ChangeSortForm
from ..model_factory import WebUiElement as Element, WebUiPage as Page, WebUiPagePydantic as PagePydantic
from ..forms.page import AddPageForm, EditPageForm, DeletePageForm, PageListForm, GetPageForm


@ui_test.login_post("/page/list", response_model=List[PagePydantic], summary="获取页面列表")
async def ui_get_page_list(form: PageListForm, request: Request):
    query_data = await form.make_pagination(Page, user=request.state.user)
    return request.app.get_success(data=query_data)


@ui_test.login_put("/page/sort", summary="页面列表排序")
async def ui_change_page_sort(form: ChangeSortForm, request: Request):
    await Page.change_sort(**form.dict(exclude_unset=True))
    return request.app.put_success()


@ui_test.login_post("/page/copy", summary="复制页面")
async def ui_copy_page(form: GetPageForm, request: Request):
    old_page = await form.validate_request()
    new_page = await Page.model_create(dict(old_page), user=request.state.user)  # 创建页面
    await Element.copy_element(old_page.id, new_page.id, request.state.user)  # 复制元素
    return request.app.success("复制成功", data=new_page)


@ui_test.login_post("/page/detail", summary="获取页面详情")
async def ui_get_page_detail(form: GetPageForm, request: Request):
    project = await form.validate_request(request)
    return request.app.get_success(project)


@ui_test.login_post("/page", summary="新增页面")
async def ui_add_page(form: AddPageForm, request: Request):
    page_list = await form.validate_request()
    if len(form.page_list) == 1:
        return request.app.post_success(data=await Page.create(**page_list[0]))
    await Page.batch_insert(page_list, request.state.user)
    return request.app.post_success()


@ui_test.login_put("/page", summary="修改页面")
async def ui_change_page(form: EditPageForm, request: Request):
    page = await form.validate_request(request)
    await page.model_update(form.dict(), request.state.user)
    return request.app.put_success()


@ui_test.login_delete("/page", summary="删除页面")
async def ui_delete_page(form: DeletePageForm, request: Request):
    page = await form.validate_request(request)
    await page.model_delete()
    return request.app.delete_success()
