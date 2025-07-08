from pathlib import Path

from loguru import logger

from utils.util.file_util import LOG_ADDRESS

# job 的日志
job_logger = logger.bind(name="job")
job_logger.add(Path(LOG_ADDRESS).joinpath("job.log"), colorize=True, filter=lambda record: record["extra"].get("name") == "job")


# main 的日志
logger = logger.bind(name="main")
logger.add(
    Path(LOG_ADDRESS).joinpath("main.log"),
    # rotation="500 MB",    # 文件达到 500MB 时分割新文件
    rotation="00:00",       # 每天0点切割日志
    retention="30 days",    # 保留最近 30 天的日志
    compression="zip",      # 旧日志压缩为 zip 格式
    encoding="utf-8",       # 文件编码格式（避免中文乱码）
    level="DEBUG",           # 最低记录 INFO 级别日志
    colorize=True,          # 不同级别输出不同颜色
    filter=lambda record: record["extra"].get("name") == "main"
)
