#!/usr/bin/env python3
from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
禁止依存 = {
    "torch",
    "tensorflow",
    "jax",
    "transformers",
    "numpy",
    "cupy",
    "onnxruntime",
    "faiss",
}


def 禁止依存走査() -> list[str]:
    violations: list[str] = []
    for path in (ROOT / "src").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name.split(".")[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module.split(".")[0]]
            for name in names:
                if name in 禁止依存:
                    violations.append(f"{path.relative_to(ROOT)}:{name}")
    return violations


def 命令実行(args: list[str]) -> dict[str, object]:
    completed = subprocess.run(args, cwd=ROOT, text=True, capture_output=True)
    return {
        "命令": " ".join(args),
        "終了符号": completed.returncode,
        "標準出力末尾": completed.stdout[-4000:],
        "標準エラー末尾": completed.stderr[-4000:],
    }


def 内蔵参照確認() -> bool:
    from minidora_k3 import ミニドラK3, 実行状態

    runtime = ミニドラK3.内蔵参照から構築()
    checks = {
        "K3の層数は？": "93",
        "K3は各トークンで何人の専門家を選びますか？": "16",
        "K3の共有専門家数は？": "2",
        "K3の総パラメータは？": "2.8T",
    }
    for query, expected in checks.items():
        result = runtime.実行(query)
        if result.status != 実行状態.合格 or result.answer != expected:
            return False
    return True


def main() -> int:
    generation = 命令実行([sys.executable, "操作/公開K3を命令化.py"])
    tests = 命令実行([sys.executable, "-m", "pytest", "-q"])
    evaluation = 命令実行([sys.executable, "操作/評価を実行.py"])
    compileall = 命令実行([sys.executable, "-m", "compileall", "-q", "src", "操作", "試験"])
    wheel = 命令実行(
        [
            sys.executable,
            "-m",
            "pip",
            "wheel",
            ".",
            "--no-build-isolation",
            "--no-deps",
            "-w",
            "dist",
        ]
    )

    architecture_path = ROOT / "台帳/公開構造命令台帳.json"
    expected_path = ROOT / "台帳/予想テンソル役割台帳.json"
    architecture = json.loads(architecture_path.read_text(encoding="utf-8")) if architecture_path.exists() else {}
    expected = json.loads(expected_path.read_text(encoding="utf-8")) if expected_path.exists() else {}
    violations = 禁止依存走査()

    checks = {
        "公開構造台帳生成": generation["終了符号"] == 0,
        "試験": tests["終了符号"] == 0,
        "局所評価": evaluation["終了符号"] == 0,
        "構文確認": compileall["終了符号"] == 0,
        "wheel構築": wheel["終了符号"] == 0,
        "禁止ニューラル依存なし": not violations,
        "総層数93": architecture.get("時間軸", {}).get("層数") == 93,
        "KDA層数69": architecture.get("時間軸", {}).get("KDA層数") == 69,
        "門制御MLA層数24": architecture.get("時間軸", {}).get("門制御MLA層数") == 24,
        "経路選択専門器数896": architecture.get("幅軸", {}).get("経路選択専門器数") == 896,
        "各token選択数16": architecture.get("幅軸", {}).get("各token選択数") == 16,
        "共有専門器数2": architecture.get("幅軸", {}).get("共有専門器数") == 2,
        "期待台帳層数93": expected.get("期待数", {}).get("層数") == 93,
        "日本語公開API": 内蔵参照確認(),
        "重み変換器存在": (ROOT / "src/minidora_k3/重み変換.py").is_file(),
        "挙動変換器存在": (ROOT / "src/minidora_k3/挙動変換.py").is_file(),
        "日本語命令語彙存在": (ROOT / "src/minidora_k3/資料/日本語命令語彙.json").is_file(),
        "英字互換境界存在": (ROOT / "src/minidora_k3/英字互換.py").is_file(),
    }
    payload = {
        "状態": "合格" if all(checks.values()) else "失敗",
        "版": "0.3.1",
        "検査": checks,
        "実行記録": {
            "公開構造台帳生成": generation,
            "試験": tests,
            "局所評価": evaluation,
            "構文確認": compileall,
            "wheel構築": wheel,
        },
        "違反": violations,
        "主張境界": {
            "公開構造から日本語命令への射影": "実装済み",
            "公開tensor情報から役割命令への変換": "実装済み",
            "safetensors byte範囲から命令operand結合": "実装済み",
            "全2.8T重み値の意味命令化": "未成立",
            "K3完全同等": "未成立",
        },
        "日本語化境界": {
            "日本語正本": ["命令", "状態", "採否理由", "履歴", "文書", "台帳", "公開API別名"],
            "英字保持": [
                "Python構文",
                "HTTP/JSON/SHA-256/safetensors",
                "K3公式tensor名",
                "K3公式config key",
                "URL・commit SHA・license",
                "外部互換API",
            ],
        },
    }
    output = ROOT / "結果/再検証結果_0_3_1.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"状態": payload["状態"], "検査": checks}, ensure_ascii=False, indent=2))
    return 0 if payload["状態"] == "合格" else 1


if __name__ == "__main__":
    raise SystemExit(main())
