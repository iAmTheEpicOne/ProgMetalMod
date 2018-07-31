import logging

def make_logger(logger_name, logfile, logging_level=logging.DEBUG):
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging_level)
    formatter = logging.Formatter('%(levelname)s - %(name)s - %(asctime)s - %(message)s', '%Y-%m-%d %H:%M:%S')
    fh = logging.FileHandler(logfile)
    fh.setLevel(loggin_level)
    fh.setFormatter(formatter)
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger
