from fastapi import Request, Depends

from ...models.autotest.model_factory import ModelSelector
from ...schemas.autotest import page as schema


async def get_page_list(request: Request, form: schema.PageListForm = Depends()):
    models = ModelSelector(request.app.test_type)
    get_filed = models.page.get_simple_filed_list()
    if form.detail:
        get_filed.extend(["module_id", "project_id"])
    query_data = await form.make_pagination(models.page, user=request.state.user)
    return request.app.get_success(data=query_data)


async def change_page_sort(request: Request, form: schema.ChangeSortForm):
    models = ModelSelector(request.app.test_type)
    await models.page.change_sort(**form.dict(exclude_unset=True))
    return request.app.put_success()


async def copy_page(request: Request, form: schema.GetPageForm):
    models = ModelSelector(request.app.test_type)
    old_page = await models.page.filter(id=form.id).first()
    new_page = await models.page.model_create(dict(old_page), user=request.state.user)  # 创建页面
    await models.element.copy_element(old_page.id, new_page.id, request.state.user)  # 复制元素
    return request.app.success("复制成功", data=new_page)


async def get_page_detail(request: Request, form: schema.GetPageForm = Depends()):
    models = ModelSelector(request.app.test_type)
    data = await models.page.filter(id=form.id).first()
    return request.app.get_success(data)


async def add_page(request: Request, form: schema.AddPageForm):
    models = ModelSelector(request.app.test_type)
    max_num = await models.page.get_max_num()
    page_list = [{
        "project_id": form.project_id,
        "module_id": form.module_id,
        "num": max_num + index + 1,
        **page.dict()} for index, page in enumerate(form.page_list)]

    if len(page_list) == 1:
        return request.app.post_success(data=dict(await models.page.create(**page_list[0])))
    await models.page.batch_insert(page_list, request.state.user)
    return request.app.post_success()


async def change_page(request: Request, form: schema.EditPageForm):
    models = ModelSelector(request.app.test_type)
    await models.page.filter(id=form.id).update(**form.get_update_data(request.state.user.id))
    return request.app.put_success()


async def delete_page(request: Request, form: schema.GetPageForm):
    models = ModelSelector(request.app.test_type)
    await models.element.validate_is_not_exist(msg="当前页面下有元素，请先删除元素，再删除页面", page_id=form.id)
    await models.page.filter(id=form.id).delete()
    return request.app.delete_success()
