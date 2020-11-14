import os,shutil

def file_list_dedup(file_list):
    new_list=list(set(file_list))
    new_list.sort(key=file_list.index)
    return new_list 


def relpath(a,b):
    pass


def check_vfile(func):
    
    pass


def refresh_directory(path):
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path)


def create_file(path,text):
    text = [text] if isinstance(text,str) else list(text)

    if os.path.exists(path):
        os.remove(path)

    with open(path,'w') as fp:
        fp.write('\n'.join(text))

    #fp.close()
    #fp = open(path,'w')
    
    return path

if __name__ == "__main__":
    #ListProcess.relpath('a/b/c','d/e/f')
    create_file('./test.v',['456'])