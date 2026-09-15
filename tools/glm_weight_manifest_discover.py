"""旧英字名の互換入口。日本語正本へ委譲する。"""
"""旧英字名の互換起動器。現行正本は `GLM重み目録探索.py`。"""
from pathlib import Path
import runpy
if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).with_name("GLM重み目録探索.py")), run_name="__main__")
