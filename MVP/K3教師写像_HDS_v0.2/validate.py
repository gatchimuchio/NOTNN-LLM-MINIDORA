from pathlib import Path
import json,sys,unittest
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/"src"))
from minidora.compiler import 教師写像監査
mapping=教師写像監査(ROOT/"teacher"/"K3教師データ.jsonl",ROOT/"mapping"/"Layer0写像.json",ROOT/"p"/"命令形P.json")
suite=unittest.defaultTestLoader.discover(str(ROOT/"tests")); result=unittest.TextTestRunner(verbosity=2).run(suite)
report={"教師写像監査":mapping,"試験":{"実行":result.testsRun,"失敗":len(result.failures),"エラー":len(result.errors),"成功":result.wasSuccessful()},"主張境界":{"K3教師データからLayer0写像":"MVP局所成立","日本語命令P実行":"成立","表層言語と内部日本語基底の分離":"MVP例で成立","一般多言語理解":"未成立","K3同等":"未成立","frontier LLM":"未成立"}}
(ROOT/"validation"/"結果.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
if not result.wasSuccessful() or mapping["状態"]!="合格": raise SystemExit(1)
print(json.dumps(report,ensure_ascii=False,indent=2))
