"""旧英字名の互換入口。日本語正本へ委譲する。"""
"""旧英字名の互換起動器。現行正本は `リポジトリ整合性監査.py`。"""
from pathlib import Path
import runpy
if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).with_name("リポジトリ整合性監査.py")), run_name="__main__")
