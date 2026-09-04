from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from minidora.製品版 import 製品ミニドラ, 固定ニュース供給器, 固定知識供給器
from minidora.製品版.型 import 参照資料

@dataclass(frozen=True)
class Case:
    name:str; prompt:str; session:str; check:object

def core():
    try:
        from minidora import ミニドラ
        return ミニドラ()
    except Exception:
        class Fallback:
            def 応答(self,q): return "未対応"
        return Fallback()

NEWS=(参照資料("n1","新制度発表","source","https://example/1",datetime.now(timezone.utc),"新制度が発表された。来月開始する。"),)
KNOW=(参照資料("k1","富士山","Wikipedia","https://example/fuji",None,"富士山は日本最高峰で標高3776メートル。"),)
CASES=(
    Case("算術","(12+8)*3","calc",lambda r:"60" in r.本文),
    Case("基本会話","何ができる？","basic",lambda r:"ニュース" in r.本文 and "監査" in r.本文),
    Case("知識参照","富士山とは？","know",lambda r:"3776" in r.本文),
    Case("ニュース","今日のニュースは？","news",lambda r:len(r.参照)>=1),
    Case("ニュース要約","3行で要約して","news",lambda r:r.経路=="要約" and len(r.参照)>=1),
    Case("明示要約","要約して：Aは重要です。Bは補助です。Cは追加情報です。","sum",lambda r:"A" in r.本文),
)

def run(on:bool):
    app=製品ミニドラ(基礎ミニドラ=core(),ニュース供給器=固定ニュース供給器(NEWS),知識供給器=固定知識供給器(KNOW))
    if not on:
        for name in tuple(x for x in app.能力一覧() if x not in {"基礎Core","完全経路監査"}): app.Module解除(name)
    rows=[]; passed=0
    for c in CASES:
        r=app.応答(c.prompt,セッションID=c.session); ok=bool(c.check(r)); passed+=int(ok); rows.append({"case":c.name,"ok":ok,"route":r.経路,"response":r.本文[:180]})
    return {"module_on":on,"passed":passed,"total":len(CASES),"rows":rows}

if __name__=="__main__":
    off=run(False); on=run(True); report={"module_off":off,"module_on":on,"delta":on["passed"]-off["passed"]}
    print(json.dumps(report,ensure_ascii=False,indent=2))
