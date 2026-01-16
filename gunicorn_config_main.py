import multiprocessing

import config

bind = f'0.0.0.0:{config.ServerInfo.MAIN_PORT}'  # 访问地址
workers = 15 if multiprocessing.cpu_count() * 2 + 1 >= 15 else multiprocessing.cpu_count() * 2 + 1
worker_class = 'uvicorn.workers.UvicornWorker'  # 工作模式协程
threads = 4  # 每个worker的线程数
timeout = 300  # worker进程处理任务时间，根据实际情况调整，如果出现了 WORKER TIMEOUT 就调大点
keepalive = 5
