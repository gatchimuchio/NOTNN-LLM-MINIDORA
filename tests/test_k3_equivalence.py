import json
import unittest

from minidora.k3_benchmark import run_k3_equivalence_benchmark


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


if __name__ == "__main__":
    unittest.main()
