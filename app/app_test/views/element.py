import os
from typing import List
from fastapi import Request, UploadFile, File, Form
from fastapi.responses import FileResponse

from ..routers import app_test
from ...baseForm import ChangeSortForm
from ..model_factory import AppUiElement as Element, AppUiElementPydantic as ElementPydantic, AppUiProject as Project, \
    AppUiModule as Module, AppUiPage as Page
from ..forms.element import AddElementForm, EditElementForm, DeleteElementForm, ElementListForm, \
    GetElementForm, ChangeElementByIdForm
from utils.parse.parse_excel import parse_file_content
from utils.util.file_util import STATIC_ADDRESS
from app.config.models.config import Config


@app_test.login_post("/element/list", response_model=List[ElementPydantic], summary="获取元素列表")
async def app_get_element_list(form: ElementListForm, request: Request):
    query_data = await form.make_pagination(Element, user=request.state.user)
    return request.app.get_success(data=query_data)


@app_test.login_put("/element/sort", summary="元素列表排序")
async def app_change_element_sort(form: ChangeSortForm, request: Request):
    await Element.change_sort(**form.dict(exclude_unset=True))
    return request.app.put_success()


@app_test.login_put("/element/change", summary="根据id修改元素")
async def app_change_element_by_id(form: ChangeElementByIdForm, request: Request):
    element = await form.validate_request()
    await element.model_update(**form.dict(), user=request.state.user)
    return request.app.put_success()


@app_test.login_post("/element/template", summary="下载元素导入模板")
async def app_get_element_template(request: Request):
    return FileResponse(os.path.join(STATIC_ADDRESS, "元素导入模板.xls"))


@app_test.login_post("/element/upload", summary="从excel中导入元素")
async def app_element_upload(request: Request, file: UploadFile = File(), page_id: str = Form()):
    if page := await Page.filter(id=page_id).first() is None:
        return request.app.fail("元素不存在")
    if file and file.filename.endswith("xls"):
        # [{"元素名称": "账号输入框", "定位方式": "根据id属性定位", "元素表达式": "account", "等待元素出现的超时时间": 10.0}]
        excel_data = parse_file_content(file.read())
        option_dict = {option["label"]: option["value"] for option in Config.get_find_element_option()}
        element_list = []
        for element_data in excel_data:
            name, by = element_data.get("元素名称"), element_data.get("定位方式")
            element, wait_time_out = element_data.get("元素表达式"), element_data.get("等待元素出现的超时时间")
            if all((name, by, element, wait_time_out)):
                element_list.append(Element(
                    name=name,
                    by=option_dict[by] if by in option_dict else "id",
                    element=element,
                    wait_time_out=wait_time_out,
                    project_id=page.project_id,
                    module_id=page.module_id,
                    page_id=page.id,
                    create_user=request.state.user.id,
                    update_user=request.state.user.id,

                ))
        if len(element_list) > 0:
            await Page.bulk_create(element_list)
        return request.app.success("元素导入成功")
    return request.app.fail("请上传后缀为xls的Excel文件")


@app_test.login_post("/element/from", summary="获取元素的归属信息")
async def app_get_element_from(form: GetElementForm, request: Request):
    element = await form.validate_request()
    project = await Project.filter(id=element.project_id).first()
    module_name = await Module.get_from_path(element.module_id)
    page = await Page.filter(id=element.page_id).first()
    return request.app.get_success(f'此元素归属：【{project.name}_{module_name}_{page.name}_{element.name}】')


@app_test.login_post("/element/detail", summary="获取元素详情")
async def app_get_element_detail(form: GetElementForm, request: Request):
    element = await form.validate_request(request)
    return request.app.get_success(element)


@app_test.login_post("/element", summary="新增元素")
async def app_add_element(form: AddElementForm, request: Request):
    element_list = await form.validate_request()
    await Element.batch_insert(element_list, request.state.user)
    return request.app.post_success()


@app_test.login_put("/element", summary="修改元素")
async def app_change_element(form: EditElementForm, request: Request):
    element = await form.validate_request(request)
    await element.model_update(form.dict(), request.state.user)
    return request.app.put_success()


@app_test.login_delete("/element", summary="删除元素")
async def app_delete_element(form: DeleteElementForm, request: Request):
    element = await form.validate_request(request)
    await element.model_delete()
    return request.app.delete_success()
