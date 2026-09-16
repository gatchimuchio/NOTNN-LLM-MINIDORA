"""旧CI固定パスの互換入口。置換処理はなく、読み取り専用の監査へ委譲する。"""
from 日本語基底正規化_実行 import main

if __name__ == "__main__":
    raise SystemExit(main())
