
def join_name(*args,join_str='_'):
    return join_str.join([x for x in args if x is not None])



