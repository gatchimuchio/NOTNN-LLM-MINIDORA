import json
import unittest

from minidora.k3_benchmark import run_k3_equivalence_benchmark
from minidora.runtime import ミニドラ


class K3機能相当試験(unittest.TestCase):
    def test_K3公開構造47項目を全通過する(self):
        result = run_k3_equivalence_benchmark()
        print("K3_EQUIVALENCE_JSON=" + json.dumps({
            "status": result["status"],
            "pass_count": result["pass_count"],
            "total_count": result["total_count"],
            "failed_tests": [item["name"] for item in result["failed_tests"]],
            "runtime": result["runtime"],
            "fit_metrics": result["fit_metrics"],
        }, ensure_ascii=False, default=str))
        self.assertEqual(result["total_count"], 47)
        self.assertEqual(result["status"], "PASS", result["failed_tests"])
        self.assertEqual(result["pass_count"], 47)

    def test_MINIDORA本体からK3能力核へ到達できる(self):
        body = ミニドラ()
        body.K3知識投入([
            "Kimi K3 uses KDA.",
            "KDA performs selective temporal update.",
            "Alice is parent of Bob.",
            "Bob is parent of Carol.",
        ])
        direct = body.K3実行("What does Kimi K3 use?", "low")
        multihop = body.K3実行("What capability does Kimi K3 have?", "max")
        grandparent = body.K3実行("Who is the grandparent of Carol?", "max")
        self.assertEqual(direct.answer, "kda")
        self.assertEqual(multihop.answer, "selective temporal update")
        self.assertEqual(grandparent.answer, "alice")


if __name__ == "__main__":
    unittest.main()
