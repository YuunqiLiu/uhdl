import os,shutil

from .ExtensibleFileObject import ExtensibleFileObject

def file_list_dedup(file_list):
    new_list=list(set(file_list))
    new_list.sort(key=file_list.index)
    return new_list 


def refresh_directory(path):
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path)


def create_file(path,text):
    text = [text] if isinstance(text,str) else list(text)

    if os.path.exists(path):
        os.remove(path)

    fo = ExtensibleFileObject(keyword='UHDL')
    fo.write('\n'.join(text))
    fo.write_version('1.0.1')
    fo.save(path=path)

    return path

if __name__ == "__main__":
    create_file('./test.v',['456'])
