"""旧英字名の互換入口。現行日本語正本は `製品能力モジュール実証.py`。"""
from pathlib import Path
import runpy

_正本経路 = Path(__file__).with_name("製品能力モジュール実証.py")
_名前空間 = runpy.run_path(str(_正本経路), run_name="_minidora_互換")
for _名, _値 in _名前空間.items():
    if not _名.startswith("__"):
        globals()[_名] = _値
