from __future__ import annotations

import inspect
import unittest

import minidora.hds介入制御 as control
import minidora.hds監督選択runtime as supervised
import minidora.runtime as runtime


class HDS監督ArchitectureTest(unittest.TestCase):
    def test_active_runtimeは旧outer_HDS_wrapperをimportしない(self):
        text = inspect.getsource(runtime)
        self.assertNotIn("runtime_hds_v1", text)
        self.assertNotIn("HDS駆動選択実行", text)
        self.assertNotIn("MINIDORAHDS判断主体", text)

    def test_supervised_runtimeは旧output_only_HDSを使わない(self):
        text = inspect.getsource(supervised)
        self.assertNotIn("HDS判断主体", text)
        self.assertNotIn("HDSMINIDORA模型評価", text)
        self.assertNotIn("HDS適応候補提案実行", text)
        self.assertNotIn("HDS能力経路V2候補提案実行", text)

    def test_HDS制御は回答を生成しない(self):
        text = inspect.getsource(control.標準HDS介入制御)
        self.assertNotIn("回答ラベル", text)
        self.assertNotIn("候補得点", text)
        self.assertNotIn("COMMIT", text)


if __name__ == "__main__":
    unittest.main()
