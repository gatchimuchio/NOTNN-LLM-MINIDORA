"""複数資料・確認・再計画・回答構成を同じ会話で使う追加入口。"""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from minidora.汎用チャットCLI import main
if __name__ == '__main__': raise SystemExit(main())
