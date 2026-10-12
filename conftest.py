import os
import sys

_py_base = sys.base_prefix.replace("\\", "/")
_tcl_cand = f"{_py_base}/tcl/tcl8.6"
_tk_cand = f"{_py_base}/tcl/tk8.6"
if os.path.isdir(_tcl_cand):
    os.environ["TCL_LIBRARY"] = _tcl_cand
if os.path.isdir(_tk_cand):
    os.environ["TK_LIBRARY"] = _tk_cand
