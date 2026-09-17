"""この差分に同梱した試験だけを実行し、結果をJSONへ保存する。上流全回帰ではない。"""
from __future__ import annotations
import argparse, compileall, json, platform, sys, time, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'src'))
class 記録結果(unittest.TextTestResult):
    def __init__(self,*args,**kwargs): super().__init__(*args,**kwargs);self.項目=[]
    def addSuccess(self,test): super().addSuccess(test);self.項目.append({'試験':test.id(),'結果':'PASS'})
    def addFailure(self,test,err): super().addFailure(test,err);self.項目.append({'試験':test.id(),'結果':'FAIL','詳細':self._exc_info_to_string(err,test)})
    def addError(self,test,err): super().addError(test,err);self.項目.append({'試験':test.id(),'結果':'ERROR','詳細':self._exc_info_to_string(err,test)})
    def addSkip(self,test,reason): super().addSkip(test,reason);self.項目.append({'試験':test.id(),'結果':'SKIP','理由':reason})
def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True,type=Path);args=parser.parse_args();start=time.perf_counter();syntax=all(compileall.compile_dir(ROOT/p,quiet=1,force=True) for p in ('src','tests','tools'));suite=unittest.TestSuite()
    for pattern in ('test_HDS内包統合_v2*.py','test_HDS自律接続_v3.py','test_HDS配線境界_v3.py'): suite.addTests(unittest.defaultTestLoader.discover(str(ROOT/'tests'),pattern=pattern))
    result=unittest.TextTestRunner(verbosity=2,resultclass=記録結果).run(suite);report={'対象':'同梱したHDS内包統合v3のソース切片','環境':{'OS':platform.system(),'Python':platform.python_version(),'実行器':sys.executable},'構文検査':'PASS' if syntax else 'FAIL','実行試験数':result.testsRun,'PASS':sum(x['結果']=='PASS' for x in result.項目),'FAIL':len(result.failures),'ERROR':len(result.errors),'SKIP':len(result.skipped),'経過秒':round(time.perf_counter()-start,6),'試験':result.項目,'未実行':['上流リポジトリ全試験','Windows','Python 3.11/3.12/3.14','GPQA','実HDSコンパイラ接続','既存能力モジュール全数接続','製品CLI/GUI']};args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');return 0 if result.wasSuccessful() and syntax else 1
if __name__=='__main__':raise SystemExit(main())
