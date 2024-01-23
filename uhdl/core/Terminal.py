import logging, os, inspect
#

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

        formatter = logging.Formatter("[%(levelname)s] %(message)s")
        ch.setFormatter(formatter)
        fh.setFormatter(formatter)

        self.logger.addHandler(ch)
        self.logger.addHandler(fh)


    def info(self, *args):
        self.logger.info(*args)

    def error(self, *args):
        self.logger.error(*args)

    def warning(self,string):
        self.logger.warning(string)


####################################################################################
# Lint 
####################################################################################

    def lint_info(self, string):
        self.info('[lint] %s' % string)


    # def lint_unconnect(self, op):
    #     from .Variable import Input
    #     if isinstance(op, Input):
    #         src_obj = op.father_until_component().father
    #     else:
    #         src_obj = op.father_until_component()

    #     src_path = inspect.getfile(src_obj.__class__)

    #     self.logger.warning('[lint] %s signal %s in %s is left unconnected, may be it can be fixed in file %s' \
    #                         % (op.__class__.__name__, op.full_hier, op.father_until_component().module_name, src_path))
    
    def lint_unconnect(self, op, is_top=False):
        from .Variable import Input

        if isinstance(op, Input):
            if is_top:
                src_obj = op.father_until_component()
            else:
                src_obj = op.father_until_component().father
        else:
            src_obj = op.father_until_component()

        src_path = inspect.getfile(src_obj.__class__)

        self.logger.warning('[lint] %s signal %s in %s is left unconnected, may be it can be fixed in file %s' \
                            % (op.__class__.__name__, op.full_hier, op.father_until_component().module_name, src_path))


Terminal = TerminalClass()