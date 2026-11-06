from .core import *
from .extension import *

# Avoid importing Demo at module import time to reduce circular deps.
# Access uhdl.uhdl.Demo lazily via attribute lookup.
import importlib as _importlib

def __getattr__(name):
	if name == 'Demo':
		return _importlib.import_module(__name__ + '.Demo')
	if name == 'TemplateIP':
		from .core.TemplateIP import TemplateIP
		return TemplateIP
	raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [name for name in dir() if not name.startswith('_')]