# -*- coding: utf-8 -*-
"""日本語基底移行の仕上げ用一括正規化器。PR #115 完了後に削除する。"""
from __future__ import annotations

import ast
import builtins
import io
import keyword
from pathlib import Path
import re
import tokenize

根 = Path(__file__).resolve().parents[1]

語彙 = {
    "core":"模型核", "module":"モジュール", "capability":"能力", "compiler":"構文化器",
    "architecture":"構造", "pipeline":"処理系列", "runtime":"実行系", "gate":"関門",
    "scope":"範囲", "solver":"解決器", "helper":"補助器", "benchmark":"外部評価",
    "fallback":"代替経路", "registry":"登録簿", "trace":"追跡", "checkpoint":"検査点",
    "manifest":"目録", "inventory":"目録", "candidate":"候補", "relation":"関係",
    "state":"状態", "action":"作用", "result":"結果", "source":"情報源", "summary":"要約",
    "choice":"選択肢", "context":"文脈", "reference":"参照", "projection":"射影",
    "semantic":"意味", "reasoning":"推論", "effort":"計算量", "adapter":"適合器",
    "model":"模型", "language":"言語", "roundtrip":"往復", "dependency":"依存",
    "normalization":"正規化", "budget":"予算", "priority":"優先度", "roles":"役割",
    "role":"役割", "graph":"関係図", "data":"資料", "verifier":"検証器", "evidence":"証拠",
    "quality":"品質", "replay":"再生", "capture":"記録", "compare":"比較", "eval":"評価",
    "residual":"残差", "retrieval":"取得", "route":"経路", "confidence":"信頼度",
    "integration":"統合", "unknown":"未知", "slots":"欄", "slot":"欄", "working":"作業",
    "subject":"主体", "boundary":"境界", "chain":"連鎖", "fidelity":"忠実度",
    "qualifiers":"修飾", "qualifier":"修飾", "polarity":"極性", "preservation":"保持",
    "standard":"標準", "tokens":"字句", "token":"字句", "contract":"契約",
}

外部識別子 = set(dir(builtins)) | set(keyword.kwlist) | {
    "main","setUp","tearDown","setUpClass","tearDownClass","do_GET","do_POST","log_message",
}
外部略号 = {"HDS","K3","GPQA","HTTP","JSON","SHA","URL","CSV","IR","ABI","CLI","PMC"}

パス移行 = {
    "src/minidora/旧_layer0_v03.py":"src/minidora/旧_第0層_v03.py",
    "src/minidora/core局所観測.py":"src/minidora/模型核局所観測.py",
    "src/minidora/hds統合runtime.py":"src/minidora/HDS統合実行系.py",
    "tests/test_HDS_参照_budget.py":"tests/test_HDS_参照_予算.py",
    "tests/test_HDS_参照_priority.py":"tests/test_HDS_参照_優先度.py",
    "tests/test_HDS_直接_relation_検証.py":"tests/test_HDS_直接_関係_検証.py",
    "tests/test_K3_有向_relation.py":"tests/test_K3_有向_関係.py",
    "tests/test_hds監督architecture.py":"tests/test_HDS監督_構造.py",
    "tests/test_relation_修飾_v18.py":"tests/test_関係_修飾_v18.py",
    "tests/test_standard_参照.py":"tests/test_標準_参照.py",
    "tests/test_意味_tokens.py":"tests/test_意味_字句.py",
    "tests/test_開放_relation_実行系_v16.py":"tests/test_開放_関係_実行系_v16.py",
}
重複削除 = {
    "tests/test_Core回復方針_v1.py":"tests/test_模型核回復方針_v1.py",
    "tests/test_HDS_参照_roles.py":"tests/test_HDS参照役割.py",
}
互換移行 = {
    "src/minidora/hds候補提案runtime.py":"src/minidora/HDS候補提案実行系.py",
}
内容置換 = {
    "hds候補提案実行系":"HDS候補提案実行系",
    "hds統合実行系":"HDS統合実行系",
    "HDS再生_capture":"HDS再生記録",
    "HDS再生_eval":"HDS再生評価",
    "HDS構文化器_failure_bank":"HDS構文化失敗集",
    "HDS構文化器_failure":"HDS構文化失敗",
    "HDS構文化器_records_v1_3":"HDS構文化記録_v1_3",
    "HDS構文化器_records_v1_2":"HDS構文化記録_v1_2",
    "HDS構文化器_records_v1_1":"HDS構文化記録_v1_1",
    "HDS構文化器_records":"HDS構文化記録",
}


def _英字片(名前: str) -> list[str]:
    結果=[]
    for 英字列 in re.findall(r"[A-Za-z][A-Za-z0-9]*", 名前):
        結果.extend(re.findall(r"[A-Z]+(?=[A-Z][a-z]|\d|$)|[A-Z]?[a-z]+|[A-Z]+|\d+", 英字列) or [英字列])
    return 結果


def _要正規化(名前: str) -> bool:
    if 名前 in 外部識別子:
        return False
    return any(片 not in 外部略号 and 片.lower() in 語彙 for 片 in _英字片(名前))


def _変換(名前: str) -> str:
    if 名前 in 外部識別子:
        return 名前
    置換: list[tuple[int, int, str]] = []
    for 英字列 in re.finditer(r"[A-Za-z][A-Za-z0-9]*", 名前):
        部分文字列 = 英字列.group(0)
        for 小片 in re.finditer(r"[A-Z]+(?=[A-Z][a-z]|\d|$)|[A-Z]?[a-z]+|[A-Z]+|\d+", 部分文字列):
            語 = 小片.group(0)
            if 語 in 外部略号:
                continue
            日本語 = 語彙.get(語.lower())
            if 日本語 is not None:
                置換.append((英字列.start()+小片.start(), 英字列.start()+小片.end(), 日本語))
    if not 置換:
        return 名前
    新 = 名前
    for 開始, 終了, 日本語 in reversed(置換):
        新 = 新[:開始] + 日本語 + 新[終了:]
    return 新


def _互換本文(正本: str) -> str:
    stem=Path(正本).stem
    return (
        f'"""旧英字名の互換入口。現行日本語正本は `{Path(正本).name}`。"""\n'
        'from importlib import import_module as _読込\n'
        f'_正本 = _読込(".{stem}", __package__)\n'
        'for _名, _値 in vars(_正本).items():\n'
        '    if _名 not in {"__name__", "__package__", "__loader__", "__spec__", "__file__", "__cached__"}:\n'
        '        globals()[_名] = _値\n'
    )


def _パス整理() -> None:
    for 旧相対, 新相対 in パス移行.items():
        旧,新=根/旧相対,根/新相対
        if 旧.exists() and not 新.exists():
            新.parent.mkdir(parents=True,exist_ok=True); 旧.rename(新)
    for 旧相対, 正本相対 in 重複削除.items():
        旧,正本=根/旧相対,根/正本相対
        if 旧.exists() and 正本.exists() and 旧.read_bytes()==正本.read_bytes():
            旧.unlink()
    for 旧相対, 正本相対 in 互換移行.items():
        旧,正本=根/旧相対,根/正本相対
        if 旧.exists() and 正本.exists():
            旧.write_text(_互換本文(正本相対),encoding='utf-8')

    対応={Path(a).stem:Path(b).stem for a,b in パス移行.items()}
    対応.update({Path(a).stem:Path(b).stem for a,b in 互換移行.items()})
    対応.update({Path(a).stem:Path(b).stem for a,b in 重複削除.items()})
    for p in 根.rglob('*'):
        if not p.is_file() or p.suffix.lower() not in {'.py','.md','.yml','.yaml','.json','.toml','.txt'}:
            continue
        if p.resolve() == Path(__file__).resolve():
            continue
        if str(p.relative_to(根)).replace('\\','/').startswith(('docs/','artifacts/')):
            continue
        try: text=p.read_text(encoding='utf-8')
        except (UnicodeDecodeError,OSError): continue
        new=text
        for a,b in 対応.items(): new=new.replace(a,b)
        for a,b in 内容置換.items(): new=new.replace(a,b)
        if new!=text: p.write_text(new,encoding='utf-8')


def _現役Python() -> list[Path]:
    out=[]
    for base in (根/'src/minidora',根/'tests',根/'tools',根/'aistudio'):
        if not base.exists(): continue
        for p in base.rglob('*.py'):
            rel=p.relative_to(根).as_posix()
            try: head=p.read_text(encoding='utf-8')[:1000]
            except: continue
            if '互換入口' in head or '互換案内' in head: continue
            if p.name in {'日本語基底正規化_仕上げ.py','日本語基底詳細監査.py','日本語基底監査.py'}: continue
            if rel.startswith(('docs/','artifacts/')): continue
            out.append(p)
    return sorted(out)


def _収集():
    per={}; global_defs={}; global_args={}; global_attrs={}; internal_callables=set()
    for p in _現役Python():
        try: tree=ast.parse(p.read_text(encoding='utf-8'))
        except SyntaxError: continue
        m={}
        for n in ast.walk(tree):
            if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):
                if str(p).startswith(str(根/'src/minidora')):
                    internal_callables.add(n.name)
                if _要正規化(n.name):
                    m[n.name]=_変換(n.name)
                    if str(p).startswith(str(根/'src/minidora')):
                        global_defs[n.name]=_変換(n.name)
            if isinstance(n,ast.arg) and _要正規化(n.arg):
                m[n.arg]=_変換(n.arg); global_args.setdefault(n.arg,_変換(n.arg))
            if isinstance(n,ast.Name) and isinstance(n.ctx,(ast.Store,ast.Del)) and _要正規化(n.id):
                m[n.id]=_変換(n.id)
            if isinstance(n,ast.Attribute) and isinstance(n.ctx,(ast.Store,ast.Del)) and isinstance(n.value,ast.Name) and n.value.id in {'self','cls'} and _要正規化(n.attr):
                global_attrs[n.attr]=_変換(n.attr)
        for cls in (x for x in tree.body if isinstance(x, ast.ClassDef)):
            for stmt in cls.body:
                targets = [stmt.target] if isinstance(stmt, ast.AnnAssign) else (stmt.targets if isinstance(stmt, ast.Assign) else [])
                for target in targets:
                    if isinstance(target, ast.Name) and _要正規化(target.id):
                        global_attrs[target.id] = _変換(target.id)
        per[p]=m
    return per,global_defs,global_args,global_attrs,internal_callables


def _内部import地図(tree: ast.AST, global_defs: dict[str,str]) -> dict[str,str]:
    m={}
    for n in ast.walk(tree):
        if isinstance(n,ast.ImportFrom) and (n.level>0 or (n.module or '').startswith('minidora')):
            for a in n.names:
                if a.name=='*': continue
                local=a.asname or a.name
                if a.name in global_defs:
                    m[local]=global_defs[a.name] if a.asname is None else _変換(local)
                elif _要正規化(local):
                    m[local]=_変換(local)
    return m


def _文字列変換(s: str) -> str:
    if s in {'GET','POST','PUT','PATCH','DELETE','HEAD','OPTIONS','JSON','CSV','HTTP','URL','SHA','PMC','GPQA','HDS','K3'}:
        return s
    if s == 'the result':
        return '結果'
    if not _要正規化(s):
        return s
    日本語あり = bool(re.search(r"[ぁ-んァ-ヶ一-龠々]", s))
    if '.' in s and not s.startswith('minidora.') and not 日本語あり:
        return s
    識別子的 = bool(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.:-]*', s))
    if 日本語あり or 識別子的:
        parts=s.split('.')
        return '.'.join(_変換(x) for x in parts)
    return s


def _rewrite_file(p: Path, local_map: dict[str,str], global_defs: dict[str,str], global_args: dict[str,str], global_attrs: dict[str,str], internal_callables: set[str]) -> None:
    text=p.read_text(encoding='utf-8')
    try: tree=ast.parse(text)
    except SyntaxError: return
    local_map=dict(local_map); local_map.update(_内部import地図(tree,global_defs))

    external_roots=set()
    internal_imports=set()
    for n in ast.walk(tree):
        if isinstance(n,ast.Import):
            for a in n.names: external_roots.add(a.asname or a.name.split('.')[0])
        elif isinstance(n,ast.ImportFrom):
            internal = n.level>0 or (n.module or '').startswith('minidora')
            for a in n.names:
                local=a.asname or a.name
                (internal_imports if internal else external_roots).add(local)

    safe_attrs=set()
    attr_map={**global_defs,**global_attrs}
    for n in ast.walk(tree):
        if not isinstance(n,ast.Attribute) or n.attr not in attr_map:
            continue
        root=n.value
        while isinstance(root,ast.Attribute): root=root.value
        root_name=root.id if isinstance(root,ast.Name) else None
        if root_name in external_roots:
            continue
        if n.attr=='result' and root_name in {'future','fut'}:
            continue
        safe_attrs.add((n.lineno,n.attr))

    safe_keywords=set()
    for n in ast.walk(tree):
        if not isinstance(n,ast.Call): continue
        callee=None
        if isinstance(n.func,ast.Name): callee=n.func.id
        elif isinstance(n.func,ast.Attribute): callee=n.func.attr
        internal = bool(callee and (callee in internal_callables or callee in internal_imports or re.search(r"[ぁ-んァ-ヶ一-龠々]",callee) or callee=='replace'))
        if not internal: continue
        for kw in n.keywords:
            if kw.arg and (kw.arg in global_args or kw.arg in global_attrs):
                safe_keywords.add((kw.lineno,kw.arg))

    toks=list(tokenize.generate_tokens(io.StringIO(text).readline))
    sig_index=[]
    for i,t in enumerate(toks):
        if t.type not in {tokenize.ENCODING,tokenize.NL,tokenize.NEWLINE,tokenize.INDENT,tokenize.DEDENT,tokenize.COMMENT}: sig_index.append(i)
    next_sig={}
    for a,b in zip(sig_index,sig_index[1:]): next_sig[a]=toks[b]
    out=[]; prev_sig=None
    for i,tok in enumerate(toks):
        value=tok.string
        if tok.type==tokenize.NAME:
            preceded_dot=prev_sig is not None and prev_sig.type==tokenize.OP and prev_sig.string=='.'
            following=next_sig.get(i)
            keyword_like=following is not None and following.type==tokenize.OP and following.string=='='
            if value in local_map and not preceded_dot:
                value=local_map[value]
            elif preceded_dot and (tok.start[0],value) in safe_attrs:
                value=attr_map[value]
            elif keyword_like and (tok.start[0],value) in safe_keywords:
                value=global_attrs.get(value,global_args.get(value,value))
        elif tok.type==tokenize.STRING:
            try: literal=ast.literal_eval(tok.string)
            except Exception: literal=None
            if isinstance(literal,str):
                nv=_文字列変換(literal)
                if nv!=literal:
                    prefix=(re.match(r'(?i)^([rubf]*)',tok.string) or [''])[1]
                    if 'f' not in prefix.lower(): value=prefix+repr(nv)
        nt=tokenize.TokenInfo(tok.type,value,tok.start,tok.end,tok.line); out.append(nt)
        if tok.type not in {tokenize.ENCODING,tokenize.NL,tokenize.NEWLINE,tokenize.INDENT,tokenize.DEDENT,tokenize.COMMENT}: prev_sig=nt
    new=tokenize.untokenize(out)
    new=new.replace('"eval":','"評価":').replace("'eval':","'評価':")
    if new!=text: p.write_text(new,encoding='utf-8')


def main() -> int:
    _パス整理()
    per,defs,args,attrs,callables=_収集()
    for p in _現役Python():
        _rewrite_file(p,per.get(p,{}),defs,args,attrs,callables)
    print(f'仕上げ正規化: {len(per)} Python files / 定義={len(defs)} / 引数語={len(args)} / 属性語={len(attrs)}')
    return 0

if __name__=='__main__':
    raise SystemExit(main())
