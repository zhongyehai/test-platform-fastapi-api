from config import job_server_port

workers = 1  # 任务调度服务，只起一个worker
bind = f'0.0.0.0:{job_server_port}'  # 访问地址
worker_class = 'uvicorn.workers.UvicornWorker'  # 工作模式协程
