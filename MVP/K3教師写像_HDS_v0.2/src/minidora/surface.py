from __future__ import annotations
import json,re
from pathlib import Path
from .schema import 意味要求

class 表層Adapter:
    """MVP用の薄い外部言語Adapter。一般多言語理解の完成を主張しない。"""
    def __init__(self,lexicon:dict):
        self.lexicon=lexicon; self.reverse={}
        for concept,forms in lexicon.items():
            for lang,form in forms.items(): self.reverse[(lang,form.casefold())]=concept
    @classmethod
    def JSON(cls,path:str|Path): return cls(json.loads(Path(path).read_text(encoding="utf-8")))
    def concept(self,text:str,lang:str): return self.reverse.get((lang,text.strip().casefold()),text.strip())
    def 表出(self,value,lang:str):
        if value is None: return None
        forms=self.lexicon.get(str(value)); return forms.get(lang,forms.get("ja",str(value))) if forms else str(value)
    @staticmethod
    def _日本語疑問終端除去(s:str)->str:
        endings=("は何ですか？","はどこですか？","は誰ですか？","は何ですか?","はどこですか?","は誰ですか?","は何？","はどこ？","は誰？","は何?","はどこ?","は誰?","は？","は?","？","?","。")
        for ending in endings:
            if s.endswith(ending): return s[:-len(ending)]
        return s
    def 解析(self,text:str)->意味要求:
        s=text.strip()
        if re.fullmatch(r"[0-9\.\+\-\*\/\%\(\)\s]+",s): return 意味要求("算術質問",式=s,表出言語="ja")
        if "の" in s:
            core=self._日本語疑問終端除去(s); parts=[x.strip() for x in core.split("の") if x.strip()]
            if len(parts)>=2: return 意味要求("関係質問",対象=self.concept(parts[0],"ja"),関係列=tuple(self.concept(x,"ja") for x in parts[1:]),表出言語="ja")
        m=re.fullmatch(r"What is the (.+?) of (.+?)\??",s,flags=re.I)
        if m:
            relation,subject=m.group(1),m.group(2); return 意味要求("関係質問",対象=self.concept(subject,"en"),関係列=(self.concept(relation,"en"),),表出言語="en")
        m=re.fullmatch(r"(.+?)的(.+?)(?:是)?(?:哪里|什么|誰|谁)?[？?]?",s)
        if m:
            subject,relation=m.group(1),m.group(2); return 意味要求("関係質問",対象=self.concept(subject,"zh"),関係列=(self.concept(relation,"zh"),),表出言語="zh")
        raise ValueError("MVP表層Adapterでは意味要求へ写像できない")
