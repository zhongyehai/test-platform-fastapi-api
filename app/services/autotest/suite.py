import os

from fastapi.responses import FileResponse
from fastapi import Request, UploadFile, File, Form, Depends

from ...models.autotest.model_factory import ApiCaseSuite, ApiCase, AppCaseSuite, AppCase, UiCaseSuite, UiCase
from ...schemas.autotest import suite as schema
from utils.make_data.make_xmind import get_xmind_first_sheet_data
from utils.util.file_util import STATIC_ADDRESS, TEMP_FILE_ADDRESS


async def get_suite_list(request: Request, form: schema.FindCaseSuite = Depends()):
    model = ApiCaseSuite if request.app.test_type == "api" else AppCaseSuite if request.app.test_type == "app" else UiCaseSuite
    get_filed = ["id", "name", "parent", "project_id",  "suite_type"]
    query_data = await form.make_pagination(model, get_filed=get_filed)
    return request.app.get_success(data=query_data)


async def get_suite_template(request: Request):
    return FileResponse(os.path.join(STATIC_ADDRESS, "case_suite_upload_template.xmind"))


async def upload_suite(request: Request, file: UploadFile = File(), project_id: str = Form()):
    suite_model, case_model = ApiCaseSuite, ApiCase
    if request.app.test_type == "app":
        suite_model, case_model = AppCaseSuite, AppCase
    elif request.app.test_type == "ui":
        suite_model, case_model = UiCaseSuite, UiCase

    if project_id is None:
        return request.app.fail("服务必传")

    if file and file.filename.endswith("xmind"):
        # 保存文件
        file_path = os.path.join(TEMP_FILE_ADDRESS, file.filename)
        file_content = await file.read()
        with open(file_path, 'wb') as f:
            f.write(file_content)

        # 读取文件内容，并创建数据
        xmind_data = get_xmind_first_sheet_data(file_path)
        upload_res = await suite_model.upload(project_id, xmind_data, case_model)
        return request.app.success("导入完成", upload_res)
    return request.app.fail("文件格式错误")


async def change_suite_sort(request: Request, form: schema.ChangeSortForm):
    model = ApiCaseSuite if request.app.test_type == "api" else AppCaseSuite if request.app.test_type == "app" else UiCaseSuite
    await model.change_sort(**form.dict(exclude_unset=True))
    return request.app.put_success()


async def get_suite_detail(request: Request, form: schema.GetCaseSuiteForm = Depends()):
    model = ApiCaseSuite if request.app.test_type == "api" else AppCaseSuite if request.app.test_type == "app" else UiCaseSuite
    suite = await model.filter(id=form.id).first()
    return request.app.get_success(data=suite)


async def add_suite(request: Request, form: schema.AddCaseSuiteForm):
    model = ApiCaseSuite if request.app.test_type == "api" else AppCaseSuite if request.app.test_type == "app" else UiCaseSuite
    max_num = await model.get_max_num()
    suite_list = [{
        "project_id": form.project_id,
        "suite_type": form.suite_type,
        "parent": form.parent,
        "name": suite_name,
        "num": max_num + index + 1
    } for index, suite_name in enumerate(form.data_list)]
    await model.batch_insert(suite_list, request.state.user)
    return request.app.post_success()


async def change_suite(request: Request, form: schema.EditCaseSuiteForm):
    model = ApiCaseSuite if request.app.test_type == "api" else AppCaseSuite if request.app.test_type == "app" else UiCaseSuite
    suite = await model.validate_is_exist("用例集不存在", id=form.id)
    await model.filter(id=form.id).update(**form.get_update_data(request.state.user.id))

    # 如果是否修改了用例集类型，则把子用例集的类型一并修改
    if form.parent is None and form.suite_type != suite.suite_type:
        suite.suite_type = form.suite_type
        await suite.update_children_suite_type()
    return request.app.put_success(form.dict())


async def delete_suite(request: Request, form: schema.GetCaseSuiteForm):
    suite_model, case_model = ApiCaseSuite, ApiCase
    if request.app.test_type == "app":
        suite_model, case_model = AppCaseSuite, AppCase
    elif request.app.test_type == "ui":
        suite_model, case_model = UiCaseSuite, UiCase

    await suite_model.validate_is_not_exist("请先删除当前用例集的子用例集", parent=form.id)
    await case_model.validate_is_not_exist("请先删除当前用例集下的用例", suite_id=form.id)
    await suite_model.filter(id=form.id).delete()
    return request.app.delete_success()
