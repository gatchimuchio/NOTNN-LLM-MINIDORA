from __future__ import annotations

import json, re, statistics, time, unittest, minidora
from minidora import HDSIR,HDS実行核,HDS座標,HDS残差,HDS文脈,ミニドラ,手順,命令,作用,実行状態

def pct(v,p):
    s=sorted(v); return s[min(len(s)-1,max(0,int(round((len(s)-1)*p))))]

def closed(text,l,r,lang,refs=()):
    proc=手順('bench:add',(命令('加算',作用.加算,引数=('$a','$b'),更新先='結果',根拠=('bench',)),),由来='bench')
    return HDSIR(原文=text,正規化文=text,認知世界ID='bench',座標=(HDS座標('a','対象.現在状態',l),HDS座標('b','対象.現在状態',r),HDS座標('action','手段.作用','加算'),HDS座標('result','目的.到達状態','加算結果')),関係=(),残差=(),意味作用履歴=(),実行核=HDS実行核('加算',('a','b'),'結果'),初期状態={'a':l,'b':r},種別='bench',閉包状態='CLOSED_FOR_OPERATION',表現状態='MEANING_PRESERVED',手順=proc,入力言語=lang,出力言語=lang,文脈引用=refs)

def opened(text,lang):
    return HDSIR(原文=text,正規化文=text,認知世界ID='bench:open',座標=(HDS座標('target','対象.実体',text),),関係=(),残差=(HDS残差('res','semantic_loss',text,'文脈参照先が存在しない'),),意味作用履歴=(),実行核=HDS実行核(),初期状態={},種別='bench-open',手順=None,入力言語=lang,出力言語=lang)

class Compiler:
    def コンパイル(self,入力,*,前回結果=None,HDS履歴=(),文脈:HDS文脈|None=None):
        low=入力.casefold(); lang='en' if re.search(r'[a-z]',low) else ('zh' if any(c in 入力 for c in '给它加等于多少') else 'ja')
        ctx=('それ' in 入力) or bool(re.search(r'\bit\b',low)) or ('它' in 入力); nums=[int(x) for x in re.findall(r'\d+',入力)]
        if ctx:
            focus=文脈.現在焦点 if 文脈 is not None else 前回結果
            return opened(入力,lang) if focus is None or not nums else closed(入力,int(focus),nums[-1],lang,('working:current_focus',))
        return opened(入力,lang) if len(nums)<2 else closed(入力,nums[0],nums[1],lang)

class Bench(unittest.TestCase):
    def test_bench(self):
        comp=Compiler(); direct={}; total=0
        cases={'ja':lambda a,b:f'{a}と{b}の和は？','en':lambda a,b:f'What is the sum of {a} and {b}?','zh':lambda a,b:f'{a}加{b}等于多少？'}
        for lang,render in cases.items():
            body=ミニドラ(HDSコンパイラ_=comp); ls=[]; ok=0; n=3000
            for i in range(n):
                a=(i*37)%10000; b=(i*73+11)%10000; t=time.perf_counter_ns(); r=body.実行(minidora.要求(render(a,b))); ls.append((time.perf_counter_ns()-t)/1e6)
                ok += int(r.値==a+b and r.採否.状態==実行状態.合格 and r.HDS_IR is not None and r.HDS_IR.入力言語==lang)
            direct[lang]={'n':n,'correct':ok,'p50_ms':statistics.median(ls),'p95_ms':pct(ls,.95)}; total+=ok
        seq=2000; turns=okturn=refs=0; ls=[]
        for i in range(seq):
            body=ミニドラ(HDSコンパイラ_=comp); exp=(i*13)%1000+3; self.assertEqual(body.実行(minidora.要求(f'{(i*13)%1000}と3の和は？')).値,exp)
            for lang,text,add in (('en','Add 4 to it',4),('zh','给它加5',5),('ja','それに6を足して',6)):
                exp+=add; t=time.perf_counter_ns(); r=body.実行(minidora.要求(text)); ls.append((time.perf_counter_ns()-t)/1e6); turns+=1
                okturn += int(r.値==exp and r.採否.状態==実行状態.合格 and r.HDS_IR is not None and r.HDS_IR.入力言語==lang)
                refs += int(r.HDS_IR is not None and 'working:current_focus' in r.HDS_IR.文脈引用)
        held=0; n=3000
        for i in range(n):
            text=('それに4を足して','Add 4 to it','给它加4')[i%3]; r=ミニドラ(HDSコンパイラ_=comp).実行(minidora.要求(text)); held+=int(r.値 is None and r.採否.状態==実行状態.保留)
        surf={'ja':ミニドラ(HDSコンパイラ_=comp).応答('2と3の和は？'),'en':ミニドラ(HDSコンパイラ_=comp).応答('What is the sum of 2 and 3?'),'zh':ミニドラ(HDSコンパイラ_=comp).応答('2加3等于多少？')}
        payload={'direct':direct,'direct_total':{'n':9000,'correct':total},'trinity_context':{'sequences':seq,'turns':turns,'correct':okturn,'context_citations':refs,'p50_ms':statistics.median(ls),'p95_ms':pct(ls,.95)},'no_context_suspend':{'n':n,'held':held},'surface_examples':surf}
        print('BENCHMARK_JSON='+json.dumps(payload,ensure_ascii=False,sort_keys=True)); self.assertEqual(total,9000); self.assertEqual(okturn,turns); self.assertEqual(refs,turns); self.assertEqual(held,n); self.assertEqual(surf,{'ja':'5です。','en':'5.','zh':'5。'})
