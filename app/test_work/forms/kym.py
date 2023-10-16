from pydantic import Field

from ...baseForm import BaseForm


class KymProjectForm(BaseForm):
    project: str = Field(..., title="服务名")


class ChangeKymForm(KymProjectForm):
    kym: dict = Field(..., title="kym内容")
