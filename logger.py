import logging
import time

def make_logger(logger_name, logfile, logging_level=logging.DEBUG):
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging_level)
    #logging.Formatter.converter = time.localtime
    formatter = logging.Formatter('%(levelname)s - %(name)s - %(asctime)s - %(message)s', '%Y-%m-%d %H:%M:%S')
    formatter.converter = time.localtime
    fh = logging.FileHandler(logfile)
    fh.setLevel(logging_level)
    fh.setFormatter(formatter)
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger
