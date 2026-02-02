from macro_engine import MacroEngine
import time

# Empty config will use defaults from MacroEngine
cfg = {}
engine = MacroEngine(cfg)
engine.update_status("Headless run: starting MacroEngine from run_macro.py")
engine.start()

try:
    while engine.running:
        time.sleep(1)
except KeyboardInterrupt:
    engine.update_status("Headless run: interrupted by user, stopping")
    engine.stop()
