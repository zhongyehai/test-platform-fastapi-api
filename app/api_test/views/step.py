from typing import List
from fastapi import Request

from ..routers import api_test
from ...busines import StepBusiness
from ...baseForm import ChangeSortForm
from ..model_factory import ApiStep as Step, ApiStepPydantic as StepPydantic, ApiCase as Case
from ..forms.step import GetStepListForm, GetStepForm, AddStepForm, EditStepForm, DeleteStepForm, \
    ChangeStepStatusForm, CopyStepForm


@api_test.login_post("/step/list", response_model=List[StepPydantic], summary="获取步骤列表")
async def api_get_api_step_list(form: GetStepListForm, request: Request):
    query_data = await form.make_pagination(Step, user=request.state.user)
    total, query_step_list = query_data["total"], query_data["data"]
    step_list = await Step.set_has_step_for_step(query_step_list, Case)
    return request.app.get_success(data={"total": len(step_list), "data": step_list})


@api_test.login_put("/step/sort", summary="步骤排序")
async def api_change_step_sort(form: ChangeSortForm, request: Request):
    await Step.change_sort(**form.dict(exclude_unset=True))
    return request.app.put_success()


@api_test.login_put("/step/status", summary="修改步骤状态（是否执行）")
async def api_change_step_status(form: ChangeStepStatusForm, request: Request):
    await Step.filter(id__in=form.id_list).update(status=form.status)
    return request.app.put_success()


@api_test.login_post("/step/copy", summary="复制步骤")
async def api_copy_step(form: CopyStepForm, request: Request):
    await StepBusiness.copy(form.id, form.case_id, Step, Case, request.state.user)
    return request.app.success("复制成功")


@api_test.login_post("/step/detail", summary="获取步骤详情")
async def api_get_step_detail(form: GetStepForm, request: Request):
    step = await form.validate_request(request)
    return request.app.get_success(data=step)


@api_test.login_post("/step", summary="新增步骤")
async def api_add_step(form: AddStepForm, request: Request):
    await form.validate_request()
    await StepBusiness.add_step(form.dict(), Step, Case, request.state.user)
    return request.app.post_success()


@api_test.login_put("/step", summary="修改步骤")
async def api_change_step(form: EditStepForm, request: Request):
    step = await form.validate_request(request)
    await step.model_update(form.dict(), request.state.user)
    return request.app.put_success()


@api_test.login_delete("/step", summary="删除步骤")
async def api_delete_step(form: DeleteStepForm, request: Request):
    await Step.filter(id__in=form.id_list).delete()
    return request.app.delete_success()
