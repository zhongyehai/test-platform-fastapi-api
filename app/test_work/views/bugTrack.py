from typing import List
from fastapi import Request

from ..routers import test_work
from ..forms.bugTrack import GetBugListForm, GetBugForm, DeleteBugForm, AddBugForm, ChangeBugForm, \
    ChangeBugStatusForm, ChangeBugReplayForm
from ..model_factory import BugTrack, BugTrackPydantic


@test_work.login_post("/bugTrack/iteration", summary="获取迭代列表")
async def get_bug_track_iteration(request: Request):
    # [('2022-03-11',), ('2022-03-25',)]
    query_list = await BugTrack.filter().distinct().values("iteration")
    return request.app.get_success(data=[query_res[0] for query_res in query_list])


@test_work.login_post("/bugTrack/list", response_model=List[BugTrackPydantic], summary="获取bug列表")
async def get_bug_track_list(form: GetBugListForm, request: Request):
    query_data = await form.make_pagination(BugTrack, user=request.state.user)
    return request.app.get_success(data=query_data)


@test_work.login_put("/bugTrack/status", summary="修改bug状态")
async def change_bug_track_status(form: ChangeBugStatusForm, request: Request):
    bug = await form.validate_request()
    bug.model_update({"status": form.status})
    return request.app.put_success()


@test_work.login_put("/bugTrack/replay", summary="修改bug是否复盘")
async def change_bug_track_replay(form: ChangeBugReplayForm, request: Request):
    bug = await form.validate_request()
    bug.model_update({"replay": form.replay})
    return request.app.put_success()


@test_work.login_post("/bugTrack/detail", summary="获取bug详情")
async def get_bug_track_detail(form: GetBugForm, request: Request):
    suite = await form.validate_request(request)
    return request.app.get_success(data=suite)


@test_work.login_post("/bugTrack", summary="新增bug")
async def add_bug_track(form: AddBugForm, request: Request):
    await form.validate_request(request)
    await BugTrack.model_create(form.dict(), request.state.user)
    return request.app.post_success()


@test_work.login_put("/bugTrack", summary="修改bug")
async def change_bug_track(form: ChangeBugForm, request: Request):
    bug = await form.validate_request(request)
    await bug.model_update(form.dict(), request.state.user)
    return request.app.put_success()


@test_work.login_delete("/bugTrack", summary="删除bug")
async def delete_bug_track(form: DeleteBugForm, request: Request):
    bug = await form.validate_request(request)
    await bug.model_delete()
    return request.app.delete_success()
