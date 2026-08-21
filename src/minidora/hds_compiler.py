from __future__ import annotations

import ast
import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Iterable

from .hds_ir import HDSIR, HDS実行核, HDS座標, HDS関係, HDS残差, HDS意味作用, 値状態
from .命令 import 作用, 命令, 手順


@dataclass(frozen=True, slots=True)
class 語義記録:
    表現: str
    概念: str
    正規形: str
    種別: str


class HDS意味資源:
    """言語表層とHDS概念の対応Data。命令Pとは分離する。"""

    def __init__(self, 記録群: Iterable[語義記録] = ()) -> None:
        self._記録群 = tuple(記録群) or self._既定日本語()

    def 候補(self, text: str) -> tuple[語義記録, ...]:
        return tuple(record for record in self._記録群 if record.表現 in text)

    @staticmethod
    def _既定日本語() -> tuple[語義記録, ...]:
        rows = (
            ("足す", "算術作用", "加算", "作用"), ("足して", "算術作用", "加算", "作用"),
            ("加える", "算術作用", "加算", "作用"), ("加えて", "算術作用", "加算", "作用"),
            ("和", "算術関係", "加算", "結果関係"),
            ("引く", "算術作用", "減算", "作用"), ("引いて", "算術作用", "減算", "作用"),
            ("差", "算術関係", "減算", "結果関係"),
            ("掛ける", "算術作用", "乗算", "作用"), ("掛けて", "算術作用", "乗算", "作用"),
            ("かける", "算術作用", "乗算", "作用"), ("かけて", "算術作用", "乗算", "作用"),
            ("積", "算術関係", "乗算", "結果関係"),
            ("割る", "算術作用", "除算", "作用"), ("割って", "算術作用", "除算", "作用"),
            ("商", "算術関係", "除算", "結果関係"),
            ("文字数", "計数対象", "文字数", "対象属性"), ("何文字", "計数対象", "文字数", "対象属性"),
            ("数えて", "計数作用", "計数", "作用"),
            ("大きい", "比較関係", "大", "比較"), ("小さい", "比較関係", "小", "比較"),
            ("等しい", "比較関係", "同値", "比較"), ("同じ", "比較関係", "同値", "比較"),
        )
        return tuple(語義記録(*row) for row in rows)


class HDSコンパイラ:
    """自然言語をHDS-IRへ射影し、局所閉包できる部分だけをLayer-0 Pへloweringする。"""

    _二項作用 = {ast.Add: 作用.加算, ast.Sub: 作用.減算, ast.Mult: 作用.乗算, ast.Div: 作用.除算}
    _比較作用 = {ast.Eq: "同値", ast.NotEq: "不同", ast.Gt: "大", ast.Lt: "小", ast.GtE: "以上", ast.LtE: "以下"}

    def __init__(self, 意味資源: HDS意味資源 | None = None) -> None:
        self.意味資源 = 意味資源 or HDS意味資源()

    def コンパイル(self, 問合せ: str) -> HDSIR:
        normalized = unicodedata.normalize("NFKC", 問合せ).strip()
        world = "cw:input:0"
        base_coords = [
            HDS座標("src", "source_text", 問合せ),
            HDS座標("target", "対象.実体", "入力が指示する対象", 値状態.未確定 if not normalized else 値状態.推定),
            HDS座標("purpose", "目的.到達状態", "入力要求に適合する結果", 値状態.推定),
            HDS座標("verify", "手段.検証・帰還", "結果が入力意味と整合すること", 値状態.推定),
        ]
        ops = [HDS意味作用("op:normalize", "翻訳/正規化", ("src",), ("normalized",), "Unicode NFKCと表記正規化", ("原文保持",))]
        base_coords.append(HDS座標("normalized", "language.normalized", normalized))

        if not normalized:
            return self._参照IR(問合せ, normalized, world, base_coords, ops, "空入力")

        expression = self._式候補(normalized)
        if expression is not None:
            compiled = self._数式IR(問合せ, normalized, expression, world, base_coords, ops)
            if compiled is not None:
                return compiled

        semantic = self._日本語意味IR(問合せ, normalized, world, base_coords, ops)
        if semantic is not None:
            return semantic

        comparison = self._日本語比較IR(問合せ, normalized, world, base_coords, ops)
        if comparison is not None:
            return comparison

        count = re.search(r"[「『\"](.+?)[」』\"](?:の|は)?(?:文字数|何文字)", normalized)
        if count is None:
            count = re.search(r"^(.+?)(?:は|って)?何文字[?？。!！]*$", normalized)
        if count and any(x.正規形 == "文字数" for x in self.意味資源.候補(normalized)):
            value = count.group(1).strip("「」『』\" ")
            coords = base_coords + [
                HDS座標("arg0", "対象.現在状態", value, 原文範囲=count.span(1)),
                HDS座標("action", "手段.作用", "計数"),
                HDS座標("result", "目的.到達状態", "文字数", 値状態.未確定),
            ]
            relations = (HDS関係("rel:count", ("action", "arg0"), ("result",), "作用→結果"),)
            ops2 = ops + [HDS意味作用("op:meaning", "意味理解", ("normalized",), ("arg0", "action", "result"), "文字数要求を計数意味へ射影", ("対象", "作用", "目的"))]
            proc = 手順("HDS-IR:計数", (命令("計数", 作用.計数, 引数=("$arg0",), 更新先="結果", 根拠=("HDS-IR",)),), 由来="HDSコンパイラ")
            return HDSIR(問合せ, normalized, world, tuple(coords), relations, (), tuple(ops2), HDS実行核("計数", ("arg0",)), {"arg0": value}, False, "計数", "CLOSED_FOR_OPERATION", "ARTICULATED", 手順=proc)

        return self._参照IR(問合せ, normalized, world, base_coords, ops, "意味作用未閉包")

    def _日本語意味IR(self, raw: str, text: str, world: str, base: list[HDS座標], ops: list[HDS意味作用]) -> HDSIR | None:
        senses = self.意味資源.候補(text)
        action_candidates = [s for s in senses if s.種別 in {"作用", "結果関係"} and s.正規形 in {"加算", "減算", "乗算", "除算"}]
        if not action_candidates:
            return None
        concepts = {s.正規形 for s in action_candidates}
        if len(concepts) != 1:
            residual = HDS残差("res:action_conflict", "semantic_loss", text, "複数の作用概念が競合し一意に閉包できない", ("action",), ("追加文脈",))
            return HDSIR(raw, text, world, tuple(base), (), (residual,), tuple(ops), HDS実行核(), {}, False, "未閉包", "OPEN")
        action = next(iter(concepts))
        numbers = [(m.group(), self._数値(m.group()), m.span()) for m in re.finditer(r"-?\d+(?:\.\d+)?", text)]
        if len(numbers) < 2:
            return None
        selected = numbers[:2]
        coords = base + [
            HDS座標("arg0", "対象.現在状態", selected[0][1], 原文範囲=selected[0][2]),
            HDS座標("arg1", "対象.現在状態", selected[1][1], 原文範囲=selected[1][2]),
            HDS座標("action", "手段.作用", action),
            HDS座標("result", "目的.到達状態", f"{action}結果", 値状態.未確定),
        ]
        relations = [
            HDS関係("rel:arg0", ("arg0",), ("action",), "作用入力"),
            HDS関係("rel:arg1", ("arg1",), ("action",), "作用入力"),
            HDS関係("rel:result", ("action",), ("result",), "作用→結果"),
        ]
        residuals: list[HDS残差] = []
        if len(numbers) > 2:
            for idx, (_, value, span) in enumerate(numbers[2:], start=2):
                cid = f"extra{idx}"
                coords.append(HDS座標(cid, "対象.現在状態", value, 値状態.留保, 原文範囲=span))
            residuals.append(HDS残差("res:extra_numbers", "inferred_unseparated", text, "二項作用に対して追加数値の役割が未分別", tuple(f"extra{i}" for i in range(2, len(numbers))), ("関係同定",)))
        ops2 = ops + [HDS意味作用("op:meaning", "意味理解/射影", ("normalized",), ("arg0", "arg1", "action", "result"), f"語義Dataから{action}へ射影", ("原数値", "作用意味", "結果目的"), tuple(r.理由 for r in residuals))]
        op_enum = {"加算": 作用.加算, "減算": 作用.減算, "乗算": 作用.乗算, "除算": 作用.除算}[action]
        proc = 手順(f"HDS-IR:{action}", (命令(action, op_enum, 引数=("$arg0", "$arg1"), 更新先="結果", 根拠=("HDS-IR",)),), 由来="HDSコンパイラ")
        return HDSIR(raw, text, world, tuple(coords), tuple(relations), tuple(residuals), tuple(ops2), HDS実行核(action, ("arg0", "arg1")), {"arg0": selected[0][1], "arg1": selected[1][1]}, False, "算術", "CLOSED_FOR_OPERATION" if not residuals else "PARTIALLY_CLOSED", "ARTICULATED" if not residuals else "PARTIALLY_ARTICULATED", 手順=proc if not residuals else None)

    def _日本語比較IR(self, raw: str, text: str, world: str, base: list[HDS座標], ops: list[HDS意味作用]) -> HDSIR | None:
        senses = [s for s in self.意味資源.候補(text) if s.種別 == "比較"]
        if not senses:
            return None
        relation_set = {s.正規形 for s in senses}
        if len(relation_set) != 1:
            return None
        relation = next(iter(relation_set))
        mentions = [(self._数値(m.group()), m.span()) for m in re.finditer(r"-?\d+(?:\.\d+)?", text)]
        unique: list[tuple[int | float, tuple[int, int]]] = []
        for item in mentions:
            if not any(item[0] == seen[0] for seen in unique):
                unique.append(item)
        if len(unique) != 2:
            return None
        left, right = unique[0][0], unique[1][0]
        coords = base + [
            HDS座標("arg0", "対象.現在状態", left, 原文範囲=unique[0][1]),
            HDS座標("arg1", "対象.現在状態", right, 原文範囲=unique[1][1]),
            HDS座標("action", "手段.作用", "比較"),
            HDS座標("criterion", "目的.評価規則", relation),
            HDS座標("result", "目的.到達状態", "真偽", 値状態.未確定),
        ]
        relation_list = [
            HDS関係("rel:cmp_inputs", ("arg0", "arg1"), ("action",), "比較入力"),
            HDS関係("rel:cmp_rule", ("criterion", "action"), ("result",), "評価規則→結果"),
        ]
        if len(mentions) > 2:
            for index, (value, span) in enumerate(mentions[2:], start=2):
                target = "arg0" if value == left else "arg1" if value == right else None
                if target is not None:
                    mention_id = f"mention{index}"
                    coords.append(HDS座標(mention_id, "文脈.同一性参照", value, 原文範囲=span))
                    relation_list.append(HDS関係(f"rel:{mention_id}", (mention_id,), (target,), "同一対象参照"))
        relations = tuple(relation_list)
        ops2 = ops + [HDS意味作用("op:comparison", "意味理解/射影", ("normalized",), ("arg0", "arg1", "criterion", "result"), f"比較表現を{relation}関係へ射影", ("比較対象", "評価規則", "真偽目的"))]
        proc = 手順("HDS-IR:比較", (命令("比較", 作用.比較, 引数=("$arg0", relation, "$arg1"), 更新先="結果", 根拠=("HDS-IR",)),), 由来="HDSコンパイラ")
        return HDSIR(raw, text, world, tuple(coords), relations, (), tuple(ops2), HDS実行核("比較", ("arg0", "arg1"), "結果", (), ("評価規則適用",)), {"arg0": left, "arg1": right}, False, "比較", "CLOSED_FOR_OPERATION", "ARTICULATED", 手順=proc)

    def _式候補(self, text: str) -> str | None:
        normalized = text.replace("×", "*").replace("÷", "/")
        trimmed = re.sub(r"(?:は)?[?？。!！]+$", "", normalized).strip()
        trimmed = re.sub(r"(?:を)?(?:計算して|計算|求めて|求める)$", "", trimmed).strip()
        if re.fullmatch(r"[\d\s.+\-*/()<>!=]+", trimmed) and any(op in trimmed for op in "+-*/<>=!"):
            return trimmed
        return None

    def _数式IR(self, raw: str, text: str, expr: str, world: str, base: list[HDS座標], ops: list[HDS意味作用]) -> HDSIR | None:
        try:
            tree = ast.parse(expr, mode="eval")
        except SyntaxError:
            return None
        commands: list[命令] = []
        coords = list(base)
        relations: list[HDS関係] = []
        initial: dict[str, Any] = {}
        counter = {"data": 0, "tmp": 0}

        def data_ref(value: int | float) -> str:
            key = f"arg{counter['data']}"
            counter["data"] += 1
            initial[key] = value
            coords.append(HDS座標(key, "対象.現在状態", value))
            return key

        def compile_node(node: ast.AST, target: str | None = None) -> str | None:
            if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
                return data_ref(node.value)
            if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)) and isinstance(node.operand, ast.Constant) and isinstance(node.operand.value, (int, float)):
                value = -node.operand.value if isinstance(node.op, ast.USub) else node.operand.value
                return data_ref(value)
            if isinstance(node, ast.BinOp) and type(node.op) in self._二項作用:
                left = compile_node(node.left)
                right = compile_node(node.right)
                if left is None or right is None:
                    return None
                out = target or f"tmp{counter['tmp']}"
                counter["tmp"] += 1
                action = self._二項作用[type(node.op)]
                action_id = f"action{len(commands)}"
                coords.append(HDS座標(action_id, "手段.作用", action.value))
                coords.append(HDS座標(out, "対象.現在状態" if target is None else "目的.到達状態", "未計算", 値状態.未確定))
                relations.append(HDS関係(f"rel:{action_id}", (left, right, action_id), (out,), "作用→結果"))
                commands.append(命令(action_id, action, 引数=(f"${left}", f"${right}"), 更新先="結果" if target == "result" else out, 根拠=("HDS-IR",)))
                return "結果" if target == "result" else out
            if isinstance(node, ast.Compare) and len(node.ops) == 1 and len(node.comparators) == 1 and type(node.ops[0]) in self._比較作用:
                left = compile_node(node.left)
                right = compile_node(node.comparators[0])
                if left is None or right is None:
                    return None
                out = target or "result"
                coords.append(HDS座標("action_cmp", "手段.作用", "比較"))
                coords.append(HDS座標(out, "目的.到達状態", "真偽", 値状態.未確定))
                relations.append(HDS関係("rel:cmp", (left, right, "action_cmp"), (out,), "比較→真偽"))
                commands.append(命令("比較", 作用.比較, 引数=(f"${left}", self._比較作用[type(node.ops[0])], f"${right}"), 更新先="結果", 根拠=("HDS-IR",)))
                return "結果"
            return None

        root = compile_node(tree.body, "result")
        if root is None or not commands:
            return None
        ops2 = ops + [HDS意味作用("op:ast", "分解/意味理解/実装", ("normalized",), tuple(c.座標ID for c in coords if c.座標ID.startswith(("arg", "action", "result", "tmp"))), "数式ASTをHDS座標・関係へ射影しPへlowering", ("演算順序", "数値", "作用", "依存関係"), (), ("AST構造保持",))]
        return HDSIR(raw, text, world, tuple(coords), tuple(relations), (), tuple(ops2), HDS実行核("数式", tuple(k for k in initial), "結果", ("0除算禁止",), ("AST構造保持",)), initial, False, "算術", "CLOSED_FOR_OPERATION", "ARTICULATED", 手順=手順("HDS-IR:数式", tuple(commands), 由来="HDSコンパイラ"))

    def _参照IR(self, raw: str, text: str, world: str, base: list[HDS座標], ops: list[HDS意味作用], reason: str) -> HDSIR:
        coords = base + [
            HDS座標("action", "手段.作用", "参照", 値状態.推定),
            HDS座標("result", "目的.到達状態", "参照Dataから意味に適合する内容", 値状態.未確定),
        ]
        relations = (HDS関係("rel:reference", ("target", "action"), ("result",), "参照→結果", 値状態=値状態.推定),)
        ops2 = ops + [HDS意味作用("op:reference", "射影", ("normalized",), ("target", "action", "result"), "現行入力だけでは実行意味を閉包できず外部参照へ接続", ("原文", "未確定対象"), (reason,))]
        proc = 手順("HDS-IR:参照", (
            命令("参照列取得", 作用.取得, 対象="参照", 更新先="参照列", 根拠=("HDS-IR",)),
            命令("先頭参照抽出", 作用.抽出, 引数=("$参照列", 0), 更新先="参照候補", 根拠=("HDS-IR",)),
            命令("参照内容抽出", 作用.抽出, 引数=("$参照候補", "内容"), 更新先="結果", 根拠=("HDS-IR",)),
        ), 由来="HDSコンパイラ")
        return HDSIR(raw, text, world, tuple(coords), relations, (), tuple(ops2), HDS実行核("参照", ("target",), "結果", ("根拠不足時保留",), ("出典保持",)), {}, True, "参照", "PARTIALLY_CLOSED", "PARTIALLY_ARTICULATED", 手順=proc)

    @staticmethod
    def _数値(raw: str) -> int | float:
        value = float(raw)
        return int(value) if value.is_integer() else value

    def 参照統合(self, ir: HDSIR, 参照群: tuple[Any, ...]) -> HDSIR:
        """外部Dataを同じHDS意味空間へ射影する。意味がないDataへ意味を捏造しない。"""
        if not 参照群:
            return ir
        coords = list(ir.座標)
        relations = list(ir.関係)
        residuals = list(ir.残差)
        operators = list(ir.意味作用履歴)
        semantic_slots: dict[tuple[Any, ...], list[tuple[int, Any]]] = {}

        for index, record in enumerate(参照群):
            rid = f"ref{index}"
            coords.append(HDS座標(f"{rid}.対象", "参照.対象", getattr(record, "対象", ""), 由来=getattr(record, "由来", "外部参照")))
            coords.append(HDS座標(f"{rid}.内容", "参照.内容", getattr(record, "内容", ""), 由来=getattr(record, "由来", "外部参照")))
            meaning_raw = getattr(record, "意味", ()) or ()
            meaning = dict(meaning_raw) if not isinstance(meaning_raw, dict) else dict(meaning_raw)
            for key, value in meaning.items():
                coords.append(HDS座標(f"{rid}.意味.{key}", f"参照.意味.{key}", value, 由来=getattr(record, "由来", "外部参照")))
                relations.append(HDS関係(f"rel:{rid}:{key}", (f"{rid}.対象",), (f"{rid}.意味.{key}",), "対象→意味属性", 由来=getattr(record, "由来", "外部参照")))
            if "値" in meaning:
                identity = meaning.get("実体", meaning.get("対象", getattr(record, "対象", None)))
                attribute = meaning.get("属性")
                time = meaning.get("時点")
                scope = meaning.get("範囲")
                if identity is not None and attribute is not None:
                    semantic_slots.setdefault((identity, attribute, time, scope), []).append((index, meaning["値"]))

        for slot, values in semantic_slots.items():
            distinct = []
            for _, value in values:
                if value not in distinct:
                    distinct.append(value)
            if len(distinct) > 1:
                affected = tuple(f"ref{i}.意味.値" for i, _ in values)
                residuals.append(HDS残差(
                    f"res:ref_conflict:{len(residuals)}", "contradiction", str(slot),
                    "同一意味スロットに複数の異なる値が存在する", affected,
                    ("時点・範囲・対象同一性の追加分別", "信頼・由来の評価"),
                ))
                relations.append(HDS関係(f"rel:conflict:{len(relations)}", affected, affected, "矛盾", 値状態=値状態.矛盾, 由来="HDS参照統合"))

        operators.append(HDS意味作用(
            "op:reference-merge", "意味理解/射影", tuple(f"ref{i}" for i in range(len(参照群))),
            tuple(c.座標ID for c in coords if c.座標ID.startswith("ref")),
            "外部参照Dataを入力と同一HDS意味空間へ統合",
            ("対象", "内容", "明示意味", "由来"),
            tuple(r.理由 for r in residuals if r.種別 in {"contradiction", "semantic_loss"}),
        ))
        return HDSIR(
            ir.原文, ir.正規化文, ir.認知世界ID, tuple(coords), tuple(relations), tuple(residuals), tuple(operators),
            ir.実行核, dict(ir.初期状態), ir.参照必須, ir.種別, ir.閉包状態, ir.表現状態, ir.保持状態,
            ir.暫定性状態, ir.手順,
        )

    def 表面化(self, 値: Any, 状態: str, 理由: tuple[str, ...]) -> str:
        if 状態 == "保留":
            if "未解消矛盾" in 理由:
                return "判断を保留します。未解消の矛盾があります。"
            return "分かりません。確認できる根拠がありません。"
        if 状態 == "失敗":
            return "処理できません。"
        if 値 is None:
            return "分かりません。"
        if isinstance(値, bool):
            return "はい。" if 値 else "いいえ。"
        if isinstance(値, float) and 値.is_integer():
            値 = int(値)
        if isinstance(値, (int, float)):
            return f"{値}です。"
        if isinstance(値, str):
            return 値 if 値.endswith(("。", "！", "？", "!", "?")) else f"{値}。"
        return f"{値}。"
