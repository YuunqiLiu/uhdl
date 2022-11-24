import unittest
import os, sys
import re

uhdl_path = os.path.split(os.getcwd())[0]
sys.path.append(uhdl_path)

example_dir = os.path.join(os.getcwd(),'docs','example')
example_test_dir = os.path.join(os.getcwd(),'docs','example_test')

#example_file_list = [os.path.join(example_dir, x) for x in os.listdir(example_dir) if re.search('\.py',x)]


example_file_list = []
for root, dirs, files in os.walk(example_dir):
    for file in files:
        if re.search('\.py$', file):
            example_file_list.append(os.path.join(root, file))







def exec_file(file_name):
    with open(file_name, 'rb') as f:
        source_code = f.read()
    exec_code = compile(source_code, file_name, "exec")
    scope = {}
    exec(exec_code, scope)



class ExampleTest(unittest.TestCase):

    def test_example(self):

        for example_file in example_file_list:
            print('start to test example file: %s' % example_file)
            exec_file(example_file)



if __name__ == '__main__':
    
    discover_res = unittest.defaultTestLoader.discover(example_test_dir, pattern="test*.py")

    suit = unittest.TestSuite()
    suit.addTest(discover_res)

    run = unittest.TextTestRunner()
    run.run(suit)