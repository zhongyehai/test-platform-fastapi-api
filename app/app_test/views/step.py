from typing import List
from fastapi import Request

from ..routers import app_test
from ..model_factory import AppUiStep as Step, AppUiStepPydantic as StepPydantic, AppUiCase as Case
from ..forms.step import GetStepListForm, GetStepForm, AddStepForm, EditStepForm, DeleteStepForm, \
    ChangeStepStatusForm, CopyStepForm
from ...busines import StepBusiness
from ...baseForm import ChangeSortForm


@app_test.login_post("/step/list", response_model=List[StepPydantic], summary="获取步骤列表")
async def app_get_app_step_list(form: GetStepListForm, request: Request):
    query_data = await form.make_pagination(Step, user=request.state.user)
    total, query_step_list = query_data["total"], query_data["data"]
    step_list = await Step.set_has_step_for_step(query_step_list, Case)
    return request.app.get_success(data={"total": len(step_list), "data": step_list})


@app_test.login_put("/step/sort", summary="步骤排序")
async def app_change_step_sort(form: ChangeSortForm, request: Request):
    await Step.change_sort(**form.dict(exclude_unset=True))
    return request.app.put_success()


@app_test.login_put("/step/status", summary="修改步骤状态（是否执行）")
async def app_change_step_status(form: ChangeStepStatusForm, request: Request):
    await Step.filter(id__in=form.id_list).update(status=form.status)
    return request.app.put_success()


@app_test.login_post("/step/copy", summary="复制步骤")
async def app_copy_step(form: CopyStepForm, request: Request):
    await StepBusiness.copy(form.id, form.case_id, Step, Case, request.state.user)
    return request.app.success("复制成功")


@app_test.login_post("/step/detail", summary="获取步骤详情")
async def app_get_step_detail(form: GetStepForm, request: Request):
    step = await form.validate_request(request)
    return request.app.get_success(data=step)


@app_test.login_post("/step", summary="新增步骤")
async def app_add_step(form: AddStepForm, request: Request):
    await form.validate_request()
    await StepBusiness.add_step(form.dict(), Step, Case, request.state.user)
    return request.app.post_success()


@app_test.login_put("/step", summary="修改步骤")
async def app_change_step(form: EditStepForm, request: Request):
    step = await form.validate_request(request)
    await step.model_update(form.dict(), request.state.user)
    return request.app.put_success()


@app_test.login_delete("/step", summary="删除步骤")
async def app_delete_step(form: DeleteStepForm, request: Request):
    await Step.filter(id__in=form.id_list).delete()
    return request.app.delete_success()
