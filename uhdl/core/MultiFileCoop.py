import sys, os
import traceback 
import re
from enum import Enum, unique


@unique
class GlobalValue(Enum):
    globals: None
    locals:  None


def MultiFileScope(**kwargs):
    for k,v in kwargs.items():
        setattr(GlobalValue,k,v)


class InterpreterError(Exception): 
    pass



def MultiFileExec(file_path, scope=None):

    info = open(file_path,"r").read()
    file_name = os.path.basename(file_path)
    try:
        if scope is None:
            exec(info, GlobalValue.globals, GlobalValue.locals)
        else:
            exec(info, scope[0], scope[1])
    except SyntaxError as err:
        error_class = err.__class__.__name__
        detail = err.args[0]
        line_number = err.lineno

        # log_info = ("%s at line %d of %s: %s " % (error_class, line_number, file_name, detail))
        # generate_log(log_info)

    except Exception as err:
        error_class = err.__class__.__name__
        detail = err.args[0]
        cl, exc, tb = sys.exc_info()
        line_number = traceback.extract_tb(tb)[1][1]

        # log_info = ("%s\n\n%s at line %d of %s: %s" % (err, error_class, line_number, file_name, detail))
        # generate_log(log_info)
        print("--------------------------------------------------------------------------")
        print("[ErrorDetail]: %s" %err)
        print("--------------------------------------------------------------------------")
    else:
        return
    
    raise InterpreterError("%s at line %d of %s: %s " % (error_class, line_number, file_name, detail))


# other function




# def generate_log(log_info):
#     log_path = os.getcwd()
#     log_name = log_path+'/InterpreterError.log'
#     print("start generate log file: "+log_name)
#     with open(log_name, 'w') as f:
#         # f.write(log_info)
#         print(log_info, file=f)
#         f.close()
