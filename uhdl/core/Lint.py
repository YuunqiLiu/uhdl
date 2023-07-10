import logging, os, inspect
from .Variable import *

class Lint(object):


    def __init__(self, module_name):
        self.logger = logging.getLogger(module_name)
        self.logger.setLevel(logging.DEBUG)

        fpath = "%s.lint.log" % module_name

        if os.path.exists(fpath):
            os.remove(fpath)

        fh = logging.FileHandler(fpath)
        fh.setLevel(logging.DEBUG)

        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)

        formatter = logging.Formatter("[Lint] [%(levelname)s] %(message)s")
        ch.setFormatter(formatter)
        fh.setFormatter(formatter)

        self.logger.addHandler(ch)
        self.logger.addHandler(fh)

    def info(self, *args):
        self.logger.info(*args)

    def unconnect(self, op):
        if isinstance(op, Input):
            src_obj = op.father_until_component().father
        else:
            src_obj = op.father_until_component()

        src_path = inspect.getfile(src_obj.__class__)

        self.logger.warning('%s signal %s in %s is left unconnected, may be it can be fixed in file %s' % (op.__class__.__name__, op.full_hier, op.father_until_component().module_name, src_path))
        #self.logger.warning(op)
        #self.logger.warning(inspect.getmodule(op.father).__file__)
        #self.logger.warning(inspect.getfile(op.father.__class__))
        