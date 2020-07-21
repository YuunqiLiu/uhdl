

class VFile():

    def __init__(self,path,top_path,file_list):
        self.__path      = path
        self.__top_path  = top_path
        self.__file_list = file_list

    @property
    def path(self):
        return self.__path

    @property
    def top_path(self):
        return self.__top_path

    @property
    def file_list(self):
        return self.__file_list