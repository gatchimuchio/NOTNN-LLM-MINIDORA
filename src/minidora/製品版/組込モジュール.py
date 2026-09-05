from __future__ import annotations
import re
from .能力契約 import 能力文脈
from .型 import 能力結果
from .ニュース import ニュースModule
from .要約 import 汎用要約Module
from .変換 import 文脈変換Module
from .抽出 import 情報抽出Module
from .計算 import 計算Module
from .基本会話 import 基本会話Module
from .知識 import 知識参照Module本体
from .検索 import Web検索Module本体

class ニュース能力:
    名前="ニュース"; 優先度=90
    def __init__(self,body:ニュースModule): self.body=body; self.版=body.版
    def 判定(self,c:能力文脈)->float:
        s=re.sub(r"\s+","",c.入力文).casefold(); return .99 if "ニュース" in s and any(x in s for x in ("今日","最新","主要","今")) else 0
    def 実行(self,c): return self.body.実行(c.入力文)

class 要約能力:
    名前="要約"; 優先度=85
    def __init__(self,body:汎用要約Module): self.body=body; self.版=body.版
    def 判定(self,c):
        s=re.sub(r"\s+","",c.入力文).casefold(); return .98 if any(x in s for x in ("要約","まとめて","3行","三行","短くして")) and (c.直前応答 or "：" in c.入力文 or ":" in c.入力文) else 0
    def 実行(self,c):
        m=re.search(r"(?:要約|まとめ)(?:して)?\s*[:：]\s*(.+)$",c.入力文,re.S); explicit=m.group(1).strip() if m else ""
        n=3 if any(x in c.入力文 for x in ("3行","三行")) else 4
        if explicit:
            source=explicit; refs=()
        elif c.直前参照:
            source="\n".join(f"{r.題名}。{r.本文}" for r in c.直前参照); refs=c.直前参照
        else:
            source=c.直前応答; refs=()
        return self.body.実行(source,行数=n,参照=refs)

class 変換能力:
    名前="文脈変換"; 優先度=80
    def __init__(self,body:文脈変換Module): self.body=body; self.版=body.版
    def 判定(self,c):
        s=re.sub(r"\s+","",c.入力文).casefold(); return .96 if c.直前応答 and any(x in s for x in ("箇条書き","リストに","簡潔に","短く")) else 0
    def 実行(self,c): return self.body.実行(c.入力文,c.直前応答)

class 抽出能力:
    名前="情報抽出"; 優先度=78
    def __init__(self,body:情報抽出Module): self.body=body; self.版=body.版
    def 判定(self,c):
        s=c.入力文.casefold(); return .95 if any(x in s for x in ("キーワード","要点抽出","数字を抜","urlを抜","リンクを抜")) and (c.直前応答 or "：" in c.入力文 or ":" in c.入力文) else 0
    def 実行(self,c):
        explicit=c.入力文.split("：",1)[1].strip() if "：" in c.入力文 else (c.入力文.split(":",1)[1].strip() if ":" in c.入力文 else "")
        return self.body.実行(c.入力文,explicit or c.直前応答)

class 計算能力:
    名前="計算"; 優先度=88
    def __init__(self,body:計算Module): self.body=body; self.版=body.版
    def 判定(self,c):
        raw=c.入力文.strip(); return .97 if re.fullmatch(r"[\d\s\+\-\*/%().^]+",raw) else (.9 if any(x in raw for x in ("計算して","いくつ")) else 0)
    def 実行(self,c): return self.body.実行(c.入力文)

class 基本会話能力:
    名前="基本会話"; 優先度=60
    def __init__(self,body:基本会話Module): self.body=body; self.版=body.版
    def 判定(self,c):
        s=c.入力文.replace(" ","").casefold(); return .94 if any(x in s for x in ("こんにちは","おはよう","こんばんは","ありがとう","君は誰","あなたは誰","何ができる","できること")) else 0
    def 実行(self,c): return self.body.実行(c.入力文)

class Web検索能力:
    名前="Web検索"; 優先度=75
    def __init__(self,body:Web検索Module本体): self.body=body; self.版=body.版
    def 判定(self,c):
        s=re.sub(r"\s+","",c.入力文).casefold()
        explicit=("検索して","検索しろ","web検索","ウェブ検索","ネット検索","webで検索","ウェブで検索","ネットで検索","webで調べ","ウェブで調べ","ネットで調べ")
        if any(x in s for x in explicit): return .98
        if any(x in s for x in ("最新","現在","今日","今")) and any(x in s for x in ("調べて","調査して","確認して")): return .92
        return 0
    def _query(self,s):
        q=s
        for x in ("Webで検索して","webで検索して","ウェブで検索して","ネットで検索して","Web検索して","web検索して","ウェブ検索して","ネット検索して","検索してみて","検索してください","検索して","検索しろ","Webで調べて","webで調べて","ウェブで調べて","ネットで調べて","調査して","確認して","調べて"):
            q=q.replace(x,"")
        q=re.sub(r"(?:について|を)$","",q.strip(" ？?。！!"))
        return q.strip()
    def 実行(self,c):
        query=self._query(c.入力文)
        if not query: return 能力結果(False,"",保留理由="検索語が空")
        return self.body.実行(query)

class 知識参照能力:
    名前="知識参照"; 優先度=45
    def __init__(self,body:知識参照Module本体): self.body=body; self.版=body.版
    def 判定(self,c):
        s=c.入力文.strip(); return .72 if len(s)<90 and any(x in s for x in ("とは","って何","は誰","について教えて","どこにある","何年")) else 0
    def _query(self,s):
        for x in ("について教えて","とは何ですか","とは？","とは?","とは","って何","は誰","どこにある"):
            s=s.replace(x,"")
        return s.strip(" ？?。")
    def 実行(self,c): return self.body.実行(self._query(c.入力文))

class Core能力:
    名前="基礎Core"; 版="repository-current"; 優先度=-100
    def __init__(self,runner): self.runner=runner
    def 判定(self,c): return .01
    def 実行(self,c): return self.runner(c.入力文)[0]
