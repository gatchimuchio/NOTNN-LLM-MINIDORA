from __future__ import annotations

import importlib
import unittest


class 旧英字互換入口試験(unittest.TestCase):
    def test_旧英字名は日本語正本と同じ公開実体へ委譲する(self) -> None:
        対応 = (
            ("k3_benchmark", "K3評価", "K3同等性評価を実行"),
            ("k3_functional", "K3機能", "K3相当能力核"),
            ("k3_hds_native", "K3_HDSネイティブ", "HDSIRネイティブ適合器"),
            ("hds_data_k", "HDS資料K", "HDSIR知識適合器"),
            ("hds_choice_hypothesis", "HDS選択仮説", "HDS候補代入仮説群"),
            ("hds_graph_reasoning", "HDS関係図推論", "HDS意味関係図索引構築"),
            ("hds_candidate_reconcile", "HDS候補再照合", "HDS候補横断調停"),
            ("hds_replay", "HDS再生", "HDSIR辞書化"),
            ("hds_replay_capture", "HDS再生記録", "HDS選択肢再生収録"),
            ("hds_replay_eval", "HDS再生評価", "HDS再生評価"),
            ("hds_direct_relation_verifier", "HDS直接関係検証", "HDS直接関係検証"),
            ("crossref_reference", "Crossref参照", "Crossref参照供給器"),
            ("http_reference", "HTTP参照", "Wikipedia参照供給器"),
        )
        for 旧名, 正本名, 公開名 in 対応:
            with self.subTest(旧名=旧名, 正本名=正本名, 公開名=公開名):
                旧 = importlib.import_module(f"minidora.{旧名}")
                正本 = importlib.import_module(f"minidora.{正本名}")
                self.assertIs(getattr(旧, 公開名), getattr(正本, 公開名))


if __name__ == "__main__":
    unittest.main()
