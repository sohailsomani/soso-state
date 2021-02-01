import platform
import sys

if platform.python_implementation() == "PyPy" and sys.version_info >= (3,8):
    def hook(*a,**kw):
        pass
    sys.unraisablehook = hook
