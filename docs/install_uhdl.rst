

Install UHDL
=============




UHDL is a python based package, so to install UHDL, please install Python first.

UHDL can run on most python 3 versions, so any python 3.x version will work.


UHDL has not been added to pip package management, so you need to download the source code yourself. The source code can be downloaded here:

.. code-block:: shell

    https://github.com/YuunqiLiu/uhdl


After downloading the source code, you need to add the path where the uhdl folder is located to the environment variable.

If you are currently using an environment where module environments are configured and UHDL environments are set up. You can directly run

.. code-block:: shell

    module load uhdl

or use

.. code-block:: shell

    module av

to see if there are similar modules.


To test whether uhdl is installed successfully, you can enter the following command in the terminal

.. code-block:: python

    python -c "from uhdl import *"

If the terminal does not output any results, uhdl has been installed correctly.