from tortoise.contrib.fastapi import register_tortoise

import config
from utils.log import logger
from utils.message.send_report import send_server_status


# from loguru import logger

def register_app_hook(app):
    @app.on_event("startup")
    async def startup_event():
        """ 应用启动事件 """

        app.logger = logger
        app.conf = config

        # 注册orm
        register_tortoise(
            app,
            config=config.tortoise_orm_conf,
            add_exception_handlers=True
        )

        # 把标识为要进行身份验证的接口，注册到对象APP上
        from ..baseView import url_required_map
        app.url_required_map = url_required_map

        # 注册蓝图
        from app.api_test.routers import api_test
        from app.app_test.routers import app_test
        from app.ui_test.routers import ui_test
        from app.system.routers import system_router
        from app.assist.routers import assist_router
        from app.test_work.routers import test_work
        from app.tools.routers import tool
        from app.home.routers import home
        from app.config.routers import config_router
        app.include_router(api_test, prefix='/api/apiTest')
        app.include_router(app_test, prefix='/api/appTest')
        app.include_router(ui_test, prefix='/api/uiTest')
        app.include_router(system_router, prefix='/api/system')
        app.include_router(assist_router, prefix='/api/assist')
        app.include_router(test_work, prefix='/api/testWork')
        app.include_router(tool, prefix='/api/tools')
        app.include_router(home, prefix='/api/home')
        app.include_router(config_router, prefix='/api/config')

        app.logger.info(f'\n\n\n{"*" * 20} 服务【{app.title}】启动完成 {"*" * 20}\n\n\n'"")
        if config.is_linux:
            send_server_status(config.token_secret_key, app.title, action_type='启动')

    @app.on_event("shutdown")
    async def shutdown_event():
        app.logger.info(f'\n\n\n{"*" * 20} 服务【{app.title}】关闭完成 {"*" * 20}\n\n\n'"")
        if config.is_linux:
            send_server_status(config.token_secret_key, app.title, action_type='关闭')
