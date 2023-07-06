import logging, os, inspect
from .Variable import *

class TerminalClass(object):
    def __init__(self):
        self.logger = logging.getLogger('UHDL')
        self.logger.setLevel(logging.DEBUG)
        fpath = "UHDL.log"
        print(fpath)

        if os.path.exists(fpath):
            os.remove(fpath)

        fh = logging.FileHandler(fpath)
        fh.setLevel(logging.DEBUG)

        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)

        formatter = logging.Formatter("[Log] [%(levelname)s] %(message)s")
        ch.setFormatter(formatter)
        fh.setFormatter(formatter)

        self.logger.addHandler(ch)
        self.logger.addHandler(fh)

    def warning(self,string):
        self.logger.warning(string)

Terminal = TerminalClass()