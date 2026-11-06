"""pyslang across versions, imported only when SV is read.

pyslang 8.x-11.x export everything at the top level; 12.x moved the names into submodules
(pyslang.driver, pyslang.ast, pyslang.syntax). Older versions lack Driver.runFullCompilation.
UHDL supports pyslang 8.1 (Python 3.8-3.13) through 12.x (abi3, Python 3.11 and later).
"""
_SUBMODULES = ('driver', 'ast', 'syntax', 'parsing', 'analysis')


def _pyslang():
    try:
        import pyslang
    except ImportError as e:
        raise ImportError('Reading SystemVerilog (VComponent, import_sv_package, slang lint) needs pyslang: '
                          'pip install "pyslang>=8.1"') from e
    return pyslang


def get(name):
    ps = _pyslang()
    if hasattr(ps, name):
        return getattr(ps, name)
    for sub in _SUBMODULES:
        m = getattr(ps, sub, None)
        if m is not None and hasattr(m, name):
            return getattr(m, name)
    raise ImportError('pyslang %s has no %s' % (getattr(ps, '__version__', '?'), name))


def __getattr__(name):                     # from ._slang import Driver  /  _slang.SymbolKind
    if name.startswith('__'):
        raise AttributeError(name)
    return get(name)


def full_compilation(driver):
    '''Elaborate and report like `slang`; True when there are no errors.'''
    if hasattr(driver, 'runFullCompilation'):
        return driver.runFullCompilation(quiet=True)
    comp = driver.createCompilation()
    return not any(d.isError() for d in comp.getAllDiagnostics())
