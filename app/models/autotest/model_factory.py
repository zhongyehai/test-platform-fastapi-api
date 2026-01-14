from .device import *
from .project import *
from .module import *
from .element import *
from .page import *
from .suite import *
from .case import *
from .step import *
from .task import *
from .report import *
from .report_case import *
from .report_step import *

class ModelSelector:
    """模型选择器"""

    def __init__(self, test_type: str):
        match test_type:
            case "api":
                self.project = ApiProject
                self.env = ApiProjectEnv
                self.module = ApiModule
                self.api = ApiMsg
                self.suite = ApiCaseSuite
                self.case = ApiCase
                self.step = ApiStep
                self.task = ApiTask
                self.report = ApiReport
                self.report_case = ApiReportCase
                self.report_step = ApiReportStep
            case "app":
                self.run_phone = AppRunPhone
                self.run_server = AppRunServer
                self.project = AppProject
                self.env = AppProjectEnv
                self.module = AppModule
                self.page = AppPage
                self.element = AppElement
                self.suite = AppCaseSuite
                self.case = AppCase
                self.step = AppStep
                self.task = AppTask
                self.report = AppReport
                self.report_case = AppReportCase
                self.report_step = AppReportStep
            case "ui":
                self.project = UiProject
                self.env = UiProjectEnv
                self.module = UiModule
                self.page = UiPage
                self.element = UiElement
                self.suite = UiCaseSuite
                self.case = UiCase
                self.step = UiStep
                self.task = UiTask
                self.report = UiReport
                self.report_case = UiReportCase
                self.report_step = UiReportStep
