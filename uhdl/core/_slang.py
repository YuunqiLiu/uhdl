"""slang for UHDL through libuhdl_slang (native/uhdl_slang.cpp), loaded with ctypes.

The library has a C interface and no Python dependency, so one build serves every Python 3.8+
and the frozen `uhdl` command. Each query elaborates a slang command line in memory and returns
a small JSON document; see native/uhdl_slang.cpp for its shape.

The library is found at $UHDL_SLANG_LIB, else uhdl/_native/libuhdl_slang.so (built by
`python native/build.py`, shipped inside wheels and the toolkit component). The toolkit
component's plain-source copy (bin/_uhdl/pysrc/uhdl, for `uhdl pythonpath`) has no copy of its
own and uses the one of the frozen runtime next to it (bin/_uhdl/uhdl/_native).
"""
import ctypes
import json
import os

_LIB = None


def _path():
    env = os.environ.get('UHDL_SLANG_LIB')
    if env:
        return env
    pkg = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))        # .../uhdl
    own = os.path.join(pkg, '_native', 'libuhdl_slang.so')
    if os.path.isfile(own):
        return own
    runtime = os.path.join(os.path.dirname(os.path.dirname(pkg)), 'uhdl', '_native', 'libuhdl_slang.so')
    return runtime if os.path.isfile(runtime) else own


def _lib():
    global _LIB
    if _LIB is None:
        p = _path()
        if not os.path.isfile(p):
            raise ImportError('Reading SystemVerilog (VComponent, import_sv_package, slang lint) needs %s. '
                              'In a source checkout build it with `python native/build.py`.' % p)
        lib = ctypes.CDLL(p)
        for name in ('uhdl_slang_module', 'uhdl_slang_package'):
            getattr(lib, name).argtypes = [ctypes.c_char_p, ctypes.c_char_p]
            getattr(lib, name).restype = ctypes.c_void_p
        lib.uhdl_slang_check.argtypes = [ctypes.c_char_p]
        lib.uhdl_slang_check.restype = ctypes.c_void_p
        lib.uhdl_slang_free.argtypes = [ctypes.c_void_p]
        lib.uhdl_slang_version.restype = ctypes.c_char_p
        _LIB = lib
    return _LIB


def _call(fn, *args):
    lib = _lib()
    ptr = getattr(lib, fn)(*[a.encode() for a in args])
    if not ptr:
        raise MemoryError('libuhdl_slang returned no result')
    try:
        return json.loads(ctypes.string_at(ptr).decode('utf-8', 'replace'))
    finally:
        lib.uhdl_slang_free(ptr)


def version():
    return _lib().uhdl_slang_version().decode()


def module_info(cmdline, path):
    '''Ports, parameters and type parameters of instance `path` ("top" or "wrapper.child").
    Raises RuntimeError when slang cannot run the command line or the instance is missing.'''
    d = _call('uhdl_slang_module', cmdline, path)
    if not d['ok']:
        raise RuntimeError(d['error'])
    return d


def package_info(cmdline, name):
    '''Typedefs and parameters of package `name`, or None if there is no such package.'''
    d = _call('uhdl_slang_package', cmdline, name)
    if not d['ok']:
        if d['error'].startswith('package '):
            return None
        raise RuntimeError(d['error'])
    return d


def check(cmdline):
    '''Full elaboration: {"errors": n, "report": text as slang prints it}.'''
    d = _call('uhdl_slang_check', cmdline)
    if not d['ok']:
        raise RuntimeError(d['error'])
    return d
