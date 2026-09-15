"""旧英字名の互換入口。現行正本は `HDS選択再生評価.py`。"""
from pathlib import Path
import runpy

_正本経路 = Path(__file__).with_name("HDS選択再生評価.py")
_名前空間 = runpy.run_path(str(_正本経路), run_name="_minidora_互換")
for _名, _値 in _名前空間.items():
    if not _名.startswith("__"):
        globals()[_名] = _値
if __name__ == "__main__" and callable(_名前空間.get("main")):
    raise SystemExit(_名前空間["main"]())
