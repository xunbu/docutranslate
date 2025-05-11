import logging



# 创建日志对象
translater_logger = logging.getLogger("TranslaterLogger")
translater_logger.setLevel(logging.DEBUG)
#输出到控制台
console_handler = logging.StreamHandler()
translater_logger.addHandler(console_handler)