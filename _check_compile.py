import py_compile, traceback
try:
    py_compile.compile('macro_engine.py', doraise=True)
    print('OK')
except Exception:
    traceback.print_exc()
