"""MINIDORA継続状態の明示型JSON保存。

任意import・pickle・repr復元を使わず、登録済み型だけを復元する。
ファイル全体の完全性と、復元先Coreの実行契約を同時に照合する。
"""
from __future__ import annotations
from dataclasses import fields, is_dataclass
from enum import Enum
from hashlib import sha256
from pathlib import Path
import importlib
import json
import math
import os

形式 = "MINIDORA-CONTINUATION-v2"


def _型登録():
    """復元可能な型を固定moduleからだけ登録する。入力中の型名をimportしない。"""
    名群 = (
        "minidora.統合駆動_v2.認識", "minidora.統合駆動_v2.記憶",
        "minidora.統合駆動_v2.形成", "minidora.統合駆動_v2.適応記憶",
        "minidora.統合駆動_v2.政策", "minidora.統合駆動_v2.依存",
        "minidora.参照", "minidora.駆動系.契約", "minidora.駆動系.学習",
    )
    表 = {}
    for 名 in 名群:
        モジュール = importlib.import_module(名)
        for 値 in vars(モジュール).values():
            if isinstance(値, type) and 値.__module__ == 名 and (is_dataclass(値) or issubclass(値, Enum)):
                表[名 + ":" + 値.__qualname__] = 値
    return 表


def _符号化(値, 型表=None):
    型表 = _型登録() if 型表 is None else 型表
    if 値 is None or type(値) in (bool, int, str):
        return 値
    if type(値) is float:
        if not math.isfinite(値): raise ValueError("非有限値は保存できない")
        return {"float": 値.hex()}
    if isinstance(値, bytes):
        return {"bytes": 値.hex()}
    if isinstance(値, Enum):
        鍵 = type(値).__module__ + ":" + type(値).__qualname__
        if 鍵 not in 型表: raise TypeError("未登録enumは保存できない: " + 鍵)
        return {"enum": 鍵, "value": _符号化(値.value, 型表)}
    if is_dataclass(値) and not isinstance(値, type):
        鍵 = type(値).__module__ + ":" + type(値).__qualname__
        if 鍵 not in 型表: raise TypeError("未登録構造型は保存できない: " + 鍵)
        return {"type": 鍵, "fields": {f.name: _符号化(getattr(値, f.name), 型表) for f in fields(値)}}
    if isinstance(値, tuple): return {"tuple": [_符号化(x, 型表) for x in 値]}
    if isinstance(値, list): return {"list": [_符号化(x, 型表) for x in 値]}
    if isinstance(値, set):
        行 = [_符号化(x, 型表) for x in 値]
        行.sort(key=lambda x: json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
        return {"set": 行}
    if isinstance(値, frozenset):
        行 = [_符号化(x, 型表) for x in 値]
        行.sort(key=lambda x: json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
        return {"frozenset": 行}
    if isinstance(値, dict):
        行 = [[_符号化(k, 型表), _符号化(v, 型表)] for k, v in 値.items()]
        行.sort(key=lambda x: json.dumps(x[0], ensure_ascii=False, sort_keys=True, separators=(",", ":")))
        return {"dict": 行}
    raise TypeError("保存未対応型: " + type(値).__module__ + "." + type(値).__qualname__)


def _復号(値, 型表=None):
    型表 = _型登録() if 型表 is None else 型表
    if 値 is None or type(値) in (bool, int, str): return 値
    if not isinstance(値, dict) or len(値) != 1:
        raise ValueError("継続保存の型タグが不正")
    種, 内容 = next(iter(値.items()))
    if 種 == "float":
        結果 = float.fromhex(内容)
        if not math.isfinite(結果): raise ValueError("非有限値")
        return 結果
    if 種 == "bytes":
        try: return bytes.fromhex(内容)
        except (TypeError, ValueError) as exc: raise ValueError("bytes形式不正") from exc
    if 種 == "enum":
        if not isinstance(内容, str) or 内容 not in 型表: raise ValueError("未登録enum")
        # 旧形式互換は意図的に持たない。enumは専用二鍵形式を使う。
        raise ValueError("enum形式不正")
    if 種 == "type":
        # tests/security: {'type':'os:system','fields':{}} を明示拒否。
        raise ValueError("構造型形式不正")
    if 種 in ("tuple", "list", "set", "frozenset"):
        if not isinstance(内容, list): raise ValueError("列形式不正")
        seq = [_復号(x, 型表) for x in 内容]
        return {"tuple": tuple, "list": list, "set": set, "frozenset": frozenset}[種](seq)
    if 種 == "dict":
        if not isinstance(内容, list): raise ValueError("辞書形式不正")
        結果 = {}
        for 行 in 内容:
            if not isinstance(行, list) or len(行) != 2: raise ValueError("辞書要素不正")
            k, v = (_復号(x, 型表) for x in 行)
            if k in 結果: raise ValueError("辞書鍵重複")
            結果[k] = v
        return 結果
    raise ValueError("未知の型タグ")


def _復号完全(値, 型表):
    """dataclass/enumの二鍵タグを含む内部復号。公開ヘルパも未知型は拒否する。"""
    if 値 is None or type(値) in (bool, int, str): return 値
    if not isinstance(値, dict): raise ValueError("継続保存要素不正")
    if set(値) == {"float"}: return _復号(値, 型表)
    if set(値) == {"bytes"}: return _復号(値, 型表)
    if set(値) == {"enum", "value"}:
        型 = 型表.get(値["enum"])
        if 型 is None or not isinstance(型, type) or not issubclass(型, Enum): raise ValueError("未登録enum")
        return 型(_復号完全(値["value"], 型表))
    if set(値) == {"type", "fields"}:
        型 = 型表.get(値["type"])
        if 型 is None or not is_dataclass(型): raise ValueError("未登録構造型")
        欄 = 値["fields"]
        if not isinstance(欄, dict) or set(欄) != {f.name for f in fields(型)}:
            raise ValueError("構造フィールド不一致")
        return 型(**{k: _復号完全(v, 型表) for k, v in 欄.items()})
    if len(値) != 1: raise ValueError("継続保存の型タグが不正")
    種, 内容 = next(iter(値.items()))
    if 種 in ("tuple", "list", "set", "frozenset"):
        if not isinstance(内容, list): raise ValueError("列形式不正")
        seq = [_復号完全(x, 型表) for x in 内容]
        return {"tuple": tuple, "list": list, "set": set, "frozenset": frozenset}[種](seq)
    if 種 == "dict":
        if not isinstance(内容, list): raise ValueError("辞書形式不正")
        結果 = {}
        for 行 in 内容:
            if not isinstance(行, list) or len(行) != 2: raise ValueError("辞書要素不正")
            k, v = (_復号完全(x, 型表) for x in 行)
            if k in 結果: raise ValueError("辞書鍵重複")
            結果[k] = v
        return 結果
    if 種 in ("float", "bytes"): return _復号(値, 型表)
    raise ValueError("未知の型タグ")


def _正規JSON(値):
    return json.dumps(値, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _契約(中核, 型表):
    from ..HDS駆動コア import HDS駆動コア版
    from ..統合駆動_v2.政策 import HDS運用政策
    政策 = 中核.政策 if 中核.政策 is not None else HDS運用政策()
    return {
        "中核版": HDS駆動コア版,
        "最大作用回数": 中核.最大作用回数,
        "政策": _符号化(政策, 型表),
        "意味変換契約": _符号化(中核.意味変換契約, 型表),
    }


def _対象(中核):
    return {
        "継続記憶": 中核._継続記憶,
        "継続形成関係": 中核._継続形成関係,
        "継続認識": 中核._継続認識,
        "継続参照記憶": 中核._継続参照記憶,
        "関係学習状態": 中核._関係学習状態,
        "適応記憶": 中核._適応記憶.スナップショット(),
    }


def 継続状態を保存(中核, 経路, *, リポジトリ版, 完了問題番号=None):
    if not isinstance(リポジトリ版, str) or not リポジトリ版.strip(): raise ValueError("リポジトリ版が必要")
    if 完了問題番号 is not None and type(完了問題番号) is not int: raise TypeError("完了問題番号は整数または未指定")
    型表 = _型登録()
    本文 = {
        "形式": 形式,
        "リポジトリ版": リポジトリ版,
        "契約": _契約(中核, 型表),
        "完了問題番号": 完了問題番号,
        "状態": _符号化(_対象(中核), 型表),
    }
    本文["SHA256"] = sha256(_正規JSON(本文).encode("utf-8")).hexdigest()
    経路 = Path(経路); 経路.parent.mkdir(parents=True, exist_ok=True)
    仮 = 経路.with_name(経路.name + ".tmp")
    保存文字列 = _正規JSON(本文) + "\n"
    with 仮.open("w", encoding="utf-8") as f:
        f.write(保存文字列); f.flush(); os.fsync(f.fileno())
    仮.replace(経路)
    return {"経路": str(経路), "SHA256": 本文["SHA256"], "完了問題番号": 完了問題番号}


def 継続状態を復元(中核, 経路, *, リポジトリ版):
    try:
        root = json.loads(Path(経路).read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError("継続保存JSON不正") from exc
    if not isinstance(root, dict) or set(root) != {"形式", "リポジトリ版", "契約", "完了問題番号", "状態", "SHA256"}:
        raise ValueError("継続保存形式不正")
    digest = root["SHA256"]
    body = dict(root); body.pop("SHA256")
    if not isinstance(digest, str) or sha256(_正規JSON(body).encode("utf-8")).hexdigest() != digest:
        raise ValueError("継続保存の完全性不成立")
    if root["形式"] != 形式: raise ValueError("継続保存版不一致")
    if root["リポジトリ版"] != リポジトリ版: raise ValueError("リポジトリ版不一致")
    型表 = _型登録()
    if root["契約"] != _契約(中核, 型表): raise ValueError("中核実行契約不一致")
    状態 = _復号完全(root["状態"], 型表)
    必須 = {"継続記憶", "継続形成関係", "継続認識", "継続参照記憶", "関係学習状態", "適応記憶"}
    if not isinstance(状態, dict) or set(状態) != 必須: raise ValueError("継続状態項目不一致")
    # 全検査を終えてから一括反映する。失敗時は元Coreを変更しない。
    from ..統合駆動_v2.適応記憶 import HDS適応記憶
    適応 = HDS適応記憶(); 適応.復元(状態["適応記憶"])
    中核._継続記憶 = 状態["継続記憶"]
    中核._継続形成関係 = 状態["継続形成関係"]
    中核._継続認識 = 状態["継続認識"]
    中核._継続参照記憶 = 状態["継続参照記憶"]
    中核._関係学習状態 = 状態["関係学習状態"]
    中核._適応記憶 = 適応
    return root["完了問題番号"]
