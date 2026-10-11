"""文字列キー表現の再利用が既存署名と拒否境界を変えないことを照合する。"""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field, fields, is_dataclass
from enum import Enum, IntEnum
from hashlib import sha256
import json
import math
from collections.abc import Mapping
import unittest

from minidora.コア.値 import 正規化, 署名, _文字列キーJSON


def 旧正規化(値: object, _経路: frozenset[int] = frozenset()) -> object:
    """変更前の値.pyの実契約。差分比較用で製品経路へ接続しない。"""
    if isinstance(値, Enum):
        return {"列挙型": type(値).__module__ + "." + type(値).__qualname__, "値": 旧正規化(値.value)}
    if 値 is None or type(値) in (str, bool, int):
        return 値
    if type(値) is float:
        if not math.isfinite(値):
            raise ValueError("非有限数は意味署名へ入れられない")
        return {"実数": 値.hex()}
    if isinstance(値, bytes):
        return {"バイト列": 値.hex()}
    if id(値) in _経路:
        raise ValueError("循環参照を含む意味状態")
    経路 = _経路 | {id(値)}
    if isinstance(値, Mapping):
        組 = [[旧正規化(k, 経路), 旧正規化(v, 経路)] for k, v in 値.items()]
        return {"写像": sorted(組, key=lambda x: json.dumps(x[0], ensure_ascii=False, sort_keys=True))}
    if isinstance(値, (tuple, list)):
        return {"組" if isinstance(値, tuple) else "列": [旧正規化(v, 経路) for v in 値]}
    if isinstance(値, (set, frozenset)):
        return {"集合": sorted((旧正規化(v, 経路) for v in 値), key=lambda x: json.dumps(x, ensure_ascii=False, sort_keys=True))}
    契約 = getattr(値, "HDS署名値", None)
    if callable(契約):
        return {"契約型": type(値).__module__ + "." + type(値).__qualname__, "値": 旧正規化(契約(), 経路)}
    if is_dataclass(値) and not isinstance(値, type):
        return {
            "構造型": type(値).__module__ + "." + type(値).__qualname__,
            "項目": {f.name: 旧正規化(getattr(値, f.name), 経路) for f in fields(値) if f.metadata.get("意味", True)},
        }
    raise TypeError(f"意味署名契約がない型: {type(値).__module__}.{type(値).__qualname__}")


def 正準バイト(値: object) -> bytes:
    return json.dumps(値, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


class 区分(Enum):
    日本語 = "確定"
    組 = ("条件", 2)


class 数値区分(IntEnum):
    一 = 1


@dataclass
class 構造:
    名称: str
    成果: object
    非意味: object = field(default_factory=object, metadata={"意味": False})


class 署名契約:
    def __init__(self, 値):
        self.値 = 値
        self.呼出 = 0

    def HDS署名値(self):
        self.呼出 += 1
        return self.値


class 意味署名性能契約試験(unittest.TestCase):
    def setUp(self):
        _文字列キーJSON.cache_clear()

    def 同値(self, 値):
        旧 = 旧正規化(値)
        新 = 正規化(値)
        self.assertEqual(新, 旧)
        self.assertEqual(正準バイト(新), 正準バイト(旧))
        self.assertEqual(署名(値), sha256(正準バイト(旧)).hexdigest())

    def test_混合型の正準バイトと署名を維持(self):
        値 = {"日本語": [None, True, 17, -9, 0.0, -0.0, 1.25, b"\x00\xff"],
              "組": ("甲", 2), "集合": {"乙", 3}, "凍結": frozenset((False, "丙")),
              3: {("鍵", 2): "内容"}, "鍵".encode(): "バイト鍵", -0.5: "実数鍵",
              区分.日本語: 区分.組, "列挙数": 数値区分.一}
        self.同値(値)

    def test_日本語と制御文字の並び順を維持(self):
        鍵群 = ["", "通常", "漢字", "é", "e\u0301", "😀", "\"引用", "\\", "\n", "\r", "\t", "\b", "\f", "\x00", "\x1f", "\x7f", "\u2028", "\u2029"]
        self.同値({鍵: 番号 for 番号, 鍵 in enumerate(鍵群)})
        self.同値({鍵: 番号 for 番号, 鍵 in reversed(tuple(enumerate(鍵群)))})

    def test_孤立サロゲートの署名拒否を維持(self):
        値 = {"\ud800": "本文"}
        self.assertEqual(正規化(値), 旧正規化(値))
        for 方法 in (lambda: 正準バイト(旧正規化(値)), lambda: 署名(値)):
            with self.assertRaises(UnicodeEncodeError):
                方法()

    def test_写像挿入順と集合の構成順に依存しない(self):
        前 = {"条件": {"資料": "本文", "版": 4}, "成果": (3, 2, 1)}
        後 = {"成果": (3, 2, 1), "条件": {"版": 4, "資料": "本文"}}
        self.同値(前)
        self.同値(後)
        self.assertEqual(署名(前), 署名(後))
        self.assertNotEqual(署名((1, 2)), 署名([1, 2]))

    def test_可変成果の変更を毎回反映(self):
        値 = {"資料": {"本文": "初稿", "版": 1}, "依存": ["甲"], "条件": True}
        前 = 署名(値)
        for 鍵, 変更 in (("本文", "改訂"), ("版", 2)):
            値["資料"][鍵] = 変更
            self.同値(値)
            新 = 署名(値)
            self.assertNotEqual(新, 前)
            前 = 新
        値["依存"].append("乙")
        self.同値(値)
        self.assertNotEqual(署名(値), 前)

    def test_共有値を循環へ読み替えず検査する(self):
        共有 = {"本文": "同じ実体"}
        self.同値({"甲": 共有, "乙": 共有})

    def test_キャッシュ済み鍵でも非有限数を拒否(self):
        署名({"本文": 1})
        for 値 in (float("nan"), float("inf"), -float("inf")):
            for 方法 in (旧正規化, 正規化):
                with self.assertRaisesRegex(ValueError, "非有限数"):
                    方法({"本文": 値})

    def test_キャッシュ済み鍵でも循環と未契約型を拒否(self):
        署名({"本文": "正常"})
        循環 = {"本文": None}
        循環["本文"] = 循環
        for 方法 in (旧正規化, 正規化):
            with self.assertRaisesRegex(ValueError, "循環参照"):
                方法(循環)
            with self.assertRaisesRegex(TypeError, "意味署名契約"):
                方法({"本文": object()})

    def test_明示署名契約を毎回呼び可変値を検査(self):
        契約 = 署名契約({"本文": "初稿"})
        前 = 署名(契約)
        self.assertEqual(契約.呼出, 1)
        契約.値["本文"] = "改訂"
        後 = 署名(契約)
        self.assertEqual(契約.呼出, 2)
        self.assertNotEqual(前, 後)
        self.同値(契約)
        契約.値 = 契約
        with self.assertRaisesRegex(ValueError, "循環参照"):
            正規化(契約)

    def test_構造型と列挙型と意味除外を維持(self):
        値 = 構造("日本語", {"列挙": 区分.日本語, "番号": 数値区分.一})
        self.同値(値)
        前 = 署名(値)
        値.非意味 = "無関係な変更"
        self.assertEqual(署名(値), 前)
        値.成果["番号"] = 3
        self.同値(値)
        self.assertNotEqual(署名(値), 前)

    def test_キャッシュは有限で巨大文字列を保存しない(self):
        for 番号 in range(2200):
            正規化({f"短い鍵{番号}": None})
        計装 = _文字列キーJSON.cache_info()
        self.assertEqual(計装.maxsize, 2048)
        self.assertEqual(計装.currsize, 2048)
        for 長さ in (257, 100_000):
            値 = {"長" * 長さ: None}
            self.同値(値)
            self.assertEqual(_文字列キーJSON.cache_info(), 計装)

    def test_長さ境界と繰返し文字列に限定した再利用(self):
        self.同値({"短" * 256: 1})
        self.assertEqual(_文字列キーJSON.cache_info().misses, 1)
        self.assertGreaterEqual(_文字列キーJSON.cache_info().hits, 1)
        非文字 = {2: "甲", "乙".encode(): "丙", ("丁", 1): None}
        前 = _文字列キーJSON.cache_info()
        self.同値(非文字)
        self.assertEqual(_文字列キーJSON.cache_info(), 前)

    def test_並行署名も旧正準バイトと一致(self):
        def 比較(番号):
            値 = {"本文": f"資料{番号}", "条件": {"日本語": True, "番号": 番号}, "列": [番号, None, b"\0"]}
            期待 = sha256(正準バイト(旧正規化(値))).hexdigest()
            return 署名(値), 期待
        with ThreadPoolExecutor(max_workers=8) as 実行器:
            for 実測, 期待 in 実行器.map(比較, range(160)):
                self.assertEqual(実測, 期待)
        self.assertLessEqual(_文字列キーJSON.cache_info().currsize, 2048)


if __name__ == "__main__":
    unittest.main()
