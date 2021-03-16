import logging
import os
import threading
from datetime import datetime
from queue import Queue


class Log:
    def __init__(self):
        global logPath, resultPath, proDir
        proDir = os.path.split(os.path.realpath(__file__))[0]

        # 获取结果地址
        resultPath = os.path.join(proDir, '../log')
        if not os.path.exists(resultPath):
            os.mkdir(resultPath)

        # 获取日志地址
        logPath = os.path.join(resultPath, str(datetime.now().strftime('%Y%m%d')))
        if not os.path.exists(logPath):
            os.mkdir(logPath)

        self.logger = logging.getLogger('Ryan')
        self.logger.setLevel(logging.INFO)

        sh = logging.StreamHandler()
        th = logging.FileHandler(os.path.join(logPath, 'output.log'), encoding='utf-8')

        fmt = '%(levelname)s: %(asctime)s [%(name)s] [%(filename)s(%(funcName)s:%(lineno)d)] - %(message)s'
        formatter = logging.Formatter(fmt)

        sh.setFormatter(formatter)
        th.setFormatter(formatter)

        self.logger.addHandler(sh)
        self.logger.addHandler(th)

    def get_logger(self):
        """
        get logger
        :return:
        """
        return self.logger

    def build_start_line(self, case_no):
        """
        write start line
        :return:
        """
        self.logger.info("----------------" + case_no + " START----------------")

    def build_end_line(self, case_no):
        """
        write end line
        :return:
        """
        self.logger.info("----------------" + case_no + " END----------------")

    def build_case_line(self, case_name, code, msg):
        """
        write test case line
        :param case_name:
        :param code:
        :param msg:
        :return:
        """
        self.logger.info(case_name + " - Code:" + code + " - msg:" + msg)


class MyLog:
    log = None
    mutex = threading.Lock()

    def __init__(self):
        pass

    @staticmethod
    def get_log():
        if MyLog.log is None:
            MyLog.mutex.acquire()
            MyLog.log = Log()
            MyLog.mutex.release()

        return MyLog.log


logger = MyLog.get_log()
log = logger.get_logger()

if __name__ == "__main__":
    pass
