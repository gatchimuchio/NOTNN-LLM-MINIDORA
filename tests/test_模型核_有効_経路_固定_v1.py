from __future__ import annotations

import ast
from pathlib import Path
import unittest

import minidora.実行系 as 実行系


class 模型核ActivePathLockV1Test(unittest.TestCase):
    def test_実行系_transitive_import_関係図_excludes_experimental_unified_path(self) -> None:
        root = Path(実行系.__file__).resolve().parent
        forbidden = {
            "hds統一実行",
            "HDS統一状態循環",
            "hds能力経路_v2",
            "hds能力経路_v3",
            "hds適応候補調停",
            "hds統合判断主体",
            "HDS統合実行系",
            "実行系_hds_v1",
            "hds既存能力resolver",
        }
        visited: set[str] = set()
        stack = ["実行系"]
        reached_forbidden: set[str] = set()

        while stack:
            モジュール = stack.pop()
            if モジュール in visited:
                continue
            visited.add(モジュール)
            if モジュール in forbidden:
                reached_forbidden.add(モジュール)
                continue
            path = root / f"{モジュール}.py"
            if not path.exists():
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, ast.ImportFrom) or node.level != 1 or not node.module:
                    continue
                child = node.module.split(".", 1)[0]
                if (root / f"{child}.py").exists() and child not in visited:
                    stack.append(child)

        self.assertEqual(reached_forbidden, set(), f"active 実行系 reached experimental modules: {sorted(reached_forbidden)}")

    def test_実行系_選択肢_path_is_formal_模型核_plus_hds_supervisory_intervention(self) -> None:
        text = Path(実行系.__file__).read_text(encoding="utf-8")
        self.assertIn("HDS選択推論実行", text)
        self.assertIn("HDS監督選択実行", text)
        self.assertNotIn("HDS統一選択評価", text)
        self.assertNotIn("HDS統一状態Session", text)
        self.assertNotIn("評価実行=_統一評価", text)


if __name__ == "__main__":
    unittest.main()
