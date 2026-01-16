import config

bind = f'0.0.0.0:{config.ServerInfo.JOB_PORT}'  # 访问地址
workers = 1  # 任务调度服务，只起一个worker
threads = 4  # 每个worker的线程数
worker_class = 'uvicorn.workers.UvicornWorker'  # 工作模式协程
timeout = 120
keepalive = 5