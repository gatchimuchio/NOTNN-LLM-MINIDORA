"""PR #115 の固定修復を一度だけ適用・検証する移送用入口。

規則を生成・変更する正規化器ではない。既存の実行ジョブから明示実行し、
適用後にはこのファイル自身も読み取り専用の完成版へ置き換わる。
対象外の差分、内容不一致、試験失敗では停止し、ここからpushは行わない。
GitHubの承認・権限・ブランチ保護は変更しない。
"""
from __future__ import annotations
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import zlib

根 = Path(__file__).resolve().parents[1]
差分SHA256 = "e63aabeaa2442deb328c42155e5bf8ed58bca51a163a7ced865174aff8a3bde8"
移送片 = ('tools/日本語基底修復差分_1.b64', 'tools/日本語基底修復差分_2.b64', 'tools/日本語基底修復差分_3.b64')


def Git(*引数: str) -> bytes:
    return subprocess.check_output(["git", *引数], cwd=根)


def 内容SHA(内容: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(内容)).encode() + b"\0" + 内容).hexdigest()


def 検証を実行(命令列: list[str], 上限: int = 420) -> None:
    print("検証: " + " ".join(命令列), flush=True)
    結果 = subprocess.run(命令列, cwd=根, capture_output=True, text=True, timeout=上限)
    print((結果.stdout + 結果.stderr)[-12000:], flush=True)
    if 結果.returncode:
        raise RuntimeError("検証不合格: " + str(結果.returncode))


def main() -> int:
    if os.environ.get("GITHUB_REPOSITORY", "gatchimuchio/NOTNN-LLM-MINIDORA") != "gatchimuchio/NOTNN-LLM-MINIDORA":
        raise RuntimeError("対象リポジトリが異なる")
    枝 = Git("branch", "--show-current").decode().strip()
    if 枝 != "chore/japanese-base-normalization-2026-09-15":
        raise RuntimeError("対象作業枝以外では実行しない")
    if Git("status", "--porcelain").strip():
        raise RuntimeError("未確定の作業差分があるため停止")
    移送内容 = [(根 / 名前).read_text(encoding="ascii") for 名前 in 移送片]
    # 移送時の既知の二箇所だけを、前後の完全一致を条件に復元する。
    if 内容SHA(移送内容[0].encode("ascii")) == "564419f0f9ed51fb73e4331f63343c83075ed809":
        移送内容[0] = 移送内容[0].replace("dWvz+e99uM9", "dWvz+99uM9").replace("e+mb1a2RIs", "e+mb1yRIs")
    期待片 = ("da2af8ec586b54d41d1ddd1732aceaa7739df06a", "941da830b9bf2228671dccd7ff7d7225f2e67af7", "14d63a64af08138633d09766f5c34f00f40c82d6")
    if tuple(内容SHA(片.encode("ascii")) for 片 in 移送内容) != 期待片:
        raise RuntimeError("移送片の完全一致を確認できない")
    圧縮差分 = "".join(移送内容)
    生 = zlib.decompress(base64.b64decode(圧縮差分, validate=True))
    if hashlib.sha256(生).hexdigest() != 差分SHA256:
        raise RuntimeError("固定差分のSHA256が一致しない")
    差分 = json.loads(生)
    基準 = 差分["基準木"]
    変更済 = set(Git("diff", "--name-only", "--no-renames", "-z", 基準, "HEAD").decode().strip("\0").split("\0"))
    許可済 = {"tools/日本語基底正規化_実行.py", ".github/workflows/再構築CI.yml",
              ".github/workflows/GPQA科学専門能力_再生.yml", ".github/workflows/日本語基底正規化_一時適用.yml"}
    許可済.update(移送片)
    if not 変更済 <= 許可済:
        raise RuntimeError("基準以後に別の変更が存在するため停止: " + repr(sorted(変更済 - 許可済)))

    準備 = []
    確認済 = set()
    for 項目 in 差分["ファイル"]:
        相対 = 項目["経路"]
        if 相対 in 確認済 or Path(相対).is_absolute() or ".." in Path(相対).parts:
            raise RuntimeError("対象経路の不整合")
        確認済.add(相対)
        経路 = 根 / 相対
        if not 経路.resolve().is_relative_to(根):
            raise RuntimeError("対象経路が作業領域外を指す")
        if 相対 == "tools/日本語基底正規化_実行.py":
            旧内容 = Git("show", 基準 + ":" + 相対)
        else:
            旧内容 = 経路.read_bytes() if 経路.exists() else b""
            if 項目["変更前"] is None and 経路.exists():
                raise RuntimeError("新規対象が既に存在する: " + 相対)
        if 項目["変更前"] is not None and 内容SHA(旧内容) != 項目["変更前"]:
            raise RuntimeError("適用前の内容が基準と異なる: " + 相対)
        if 項目["変更後"] is None:
            準備.append((経路, None, 0))
            continue
        if "複写元" in 項目:
            新内容 = Git("show", 基準 + ":" + 項目["複写元"])
        else:
            新内容 = 旧内容
            for 開始, 終了, 置換文 in reversed(項目["差分"]):
                新内容 = 新内容[:開始] + 置換文.encode("utf-8") + 新内容[終了:]
        if 内容SHA(新内容) != 項目["変更後"]:
            raise RuntimeError("適用後の内容が固定差分と異なる: " + 相対)
        準備.append((経路, 新内容, 項目["権限"]))

    # 全ファイルを照合してから書き込む。失敗したジョブは後段のcommitへ進まない。
    for 経路, 新内容, 権限 in 準備:
        if 新内容 is None:
            経路.unlink()
        else:
            経路.parent.mkdir(parents=True, exist_ok=True)
            経路.write_bytes(新内容)
            経路.chmod(権限 & 0o777)
    for 名前 in 移送片:
        (根 / 名前).unlink()
    Git("add", "-A")
    if Git("write-tree").decode().strip() != 差分["完成木"]:
        raise RuntimeError("全ファイルtreeがローカル検証済み成果と一致しない")
    導入 = [sys.executable, "-m", "pip", "install", "-e", "."]
    if os.environ.get("GITHUB_ACTIONS") != "true":
        導入 += ["--no-build-isolation", "--no-deps"]
    検証を実行(導入, 180)
    検証を実行([sys.executable, "tools/日本語基底正規化_実行.py"])
    検証を実行([sys.executable, "-m", "compileall", "-q", "src", "tests", "tools"])
    検証を実行([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"])
    検証を実行([sys.executable, "tools/規模測定.py"])
    for 命令列 in ([sys.executable, "-m", "minidora", "2+3"], ["minidora", "2+3"]):
        確認 = subprocess.check_output(命令列, cwd=根, text=True, timeout=30)
        if 確認.strip() != "5です。":
            raise RuntimeError("起動確認の回答が不一致")
        print("起動確認: " + 確認.strip(), flush=True)
    Git("add", "-A")
    if Git("write-tree").decode().strip() != 差分["完成木"]:
        raise RuntimeError("試験による意図しない追加入力・差分が発生した")
    print("固定修復検証: 合格 / tree=" + 差分["完成木"], flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
