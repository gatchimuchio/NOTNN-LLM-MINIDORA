from __future__ import annotations

from typing import Protocol
import re

from .ガバナンス import 監査台帳
from .ニュース import RSSニュース供給器, ニュース供給器, ニュースモジュール版
from .会話状態 import 会話状態庫
from .基本会話 import 基本会話モジュール, 基本会話モジュール版
from .型 import チャット応答, ニュース項目
from .要約 import 決定論的要約器, 要約モジュール版


チャットモジュール版 = "hackathon-chat-v0.1"


class 応答可能(Protocol):
    def 応答(self, 問合せ: str) -> str: ...


def _ニュース要求(text: str) -> bool:
    compact = re.sub(r"\s+", "", text).casefold()
    return "ニュース" in compact and any(word in compact for word in ("今日", "最新", "主要", "いま", "今"))


def _要約要求(text: str) -> bool:
    compact = re.sub(r"\s+", "", text).casefold()
    return any(word in compact for word in ("要約", "まとめて", "まとめ", "短くして", "短く"))


def _明示要約対象(text: str) -> str:
    match = re.search(r"(?:要約|まとめ)(?:して)?\s*[:：]\s*(.+)$", text, flags=re.S)
    return match.group(1).strip() if match else ""


def _ニュース表示(items: tuple[ニュース項目, ...]) -> str:
    if not items:
        return "参照可能な今日のニュースを取得できませんでした。"
    lines = ["今日の主要ニュースです。"]
    for index, item in enumerate(items[:5], 1):
        source = f"（{item.出典名}）" if item.出典名 else ""
        lines.append(f"{index}. {item.題名}{source}")
    lines.append("必要なら「要約して」で、この取得結果だけを使って短くまとめます。")
    return "\n".join(lines)


class ハッカソンチャット:
    def __init__(
        self,
        *,
        ニュース供給器_: ニュース供給器 | None = None,
        基礎ミニドラ: 応答可能 | None = None,
        要約器: 決定論的要約器 | None = None,
        基本会話: 基本会話モジュール | None = None,
        状態庫: 会話状態庫 | None = None,
        監査台帳_: 監査台帳 | None = None,
    ) -> None:
        self.ニュース供給器 = ニュース供給器_ or RSSニュース供給器()
        self.基礎ミニドラ = 基礎ミニドラ
        self.要約器 = 要約器 or 決定論的要約器()
        self.基本会話 = 基本会話 or 基本会話モジュール()
        self.状態庫 = 状態庫 or 会話状態庫()
        self.監査台帳 = 監査台帳_ or 監査台帳()

    def 応答(self, 入力文: str, *, セッションID: str = "default") -> チャット応答:
        text = str(入力文 or "")
        state = self.状態庫.取得(セッションID)
        audit = self.監査台帳.開始(text, state.セッションID)
        audit.記録(
            段階="入力受理",
            モジュール="ハッカソンチャット",
            モジュール版=チャットモジュール版,
            入力={"入力文": text, "セッションID": state.セッションID},
            出力={"履歴件数": len(state.履歴), "直前経路": state.直前経路},
        )

        try:
            if _ニュース要求(text):
                return self._ニュース応答(text, state, audit)
            if _要約要求(text):
                return self._要約応答(text, state, audit)

            basic = self.基本会話.応答候補(text)
            if basic is not None:
                audit.経路設定("基本会話")
                audit.記録(
                    段階="能力実行",
                    モジュール="基本会話",
                    モジュール版=基本会話モジュール版,
                    入力=text,
                    出力=basic,
                )
                return self._確定(text, state, audit, basic, "基本会話")

            if self.基礎ミニドラ is not None:
                audit.経路設定("基礎ミニドラ")
                response = str(self.基礎ミニドラ.応答(text))
                audit.記録(
                    段階="能力実行",
                    モジュール="MINIDORA Core",
                    モジュール版="repository-current",
                    入力=text,
                    出力=response,
                )
                return self._確定(text, state, audit, response, "基礎ミニドラ")

            audit.経路設定("安全保留")
            response = "この入力を処理できる能力モジュールが接続されていません。推測で回答せず保留します。"
            audit.記録(
                段階="採否",
                モジュール="ハッカソンチャット",
                モジュール版=チャットモジュール版,
                入力=text,
                出力={"状態": "保留", "理由": "対応能力なし"},
            )
            return self._確定(text, state, audit, response, "安全保留", 最終状態="保留")
        except Exception as exc:
            audit.経路設定("失敗")
            response = "処理に失敗しました。根拠を確定できないため回答を生成しません。"
            audit.記録(
                段階="失敗",
                モジュール="ハッカソンチャット",
                モジュール版=チャットモジュール版,
                入力=text,
                出力={"例外型": type(exc).__name__, "理由": str(exc)},
            )
            return self._確定(text, state, audit, response, "失敗", 最終状態="失敗")

    def _ニュース応答(self, text, state, audit) -> チャット応答:
        audit.経路設定("ニュース")
        items = tuple(self.ニュース供給器.取得(text, 上限=8))
        audit.記録(
            段階="外部参照",
            モジュール="ニュース供給器",
            モジュール版=ニュースモジュール版,
            入力={"問合せ": text, "上限": 8},
            出力=[item.監査辞書() for item in items],
            根拠識別子=tuple(item.識別子 for item in items),
        )
        selected = items[:5]
        response = _ニュース表示(selected)
        audit.記録(
            段階="応答構成",
            モジュール="ニュース表示",
            モジュール版=チャットモジュール版,
            入力=[item.識別子 for item in selected],
            出力=response,
            根拠識別子=tuple(item.識別子 for item in selected),
        )
        return self._確定(text, state, audit, response, "ニュース", ニュース=items)

    def _要約応答(self, text, state, audit) -> チャット応答:
        audit.経路設定("要約")
        direct = _明示要約対象(text)
        if direct:
            source = direct
            response = self.要約器.文章要約(source)
            evidence = ("user:explicit-summary-source",)
            input_kind = "明示入力"
        elif state.直前ニュース:
            source = [item.監査辞書() for item in state.直前ニュース]
            response = self.要約器.ニュース要約(state.直前ニュース)
            evidence = tuple(item.識別子 for item in state.直前ニュース[:3])
            input_kind = "直前ニュース"
        elif state.直前応答:
            source = state.直前応答
            response = self.要約器.文章要約(state.直前応答)
            evidence = (f"trace:{state.直前追跡ID}",) if state.直前追跡ID else ()
            input_kind = "直前応答"
        else:
            response = "要約対象がありません。先に文章またはニュースを提示してください。"
            audit.記録(
                段階="採否",
                モジュール="要約",
                モジュール版=要約モジュール版,
                入力=text,
                出力={"状態": "保留", "理由": "要約対象なし"},
            )
            return self._確定(text, state, audit, response, "要約", 最終状態="保留")

        audit.記録(
            段階="文脈参照",
            モジュール="会話状態",
            モジュール版="conversation-state-v0.1",
            入力={"種別": input_kind, "直前追跡ID": state.直前追跡ID},
            出力=source,
            根拠識別子=evidence,
        )
        audit.記録(
            段階="能力実行",
            モジュール="決定論的要約",
            モジュール版=要約モジュール版,
            入力=source,
            出力=response,
            根拠識別子=evidence,
        )
        return self._確定(text, state, audit, response, "要約")

    def _確定(self, text, state, audit, response: str, route: str, *, 最終状態: str = "合格", ニュース: tuple[ニュース項目, ...] = ()) -> チャット応答:
        before = {"直前追跡ID": state.直前追跡ID, "直前経路": state.直前経路, "履歴件数": len(state.履歴)}
        state.記録(入力文=text, 応答文=response, 経路=route, 追跡ID=audit.追跡ID, ニュース=ニュース)
        audit.記録(
            段階="会話状態更新",
            モジュール="会話状態",
            モジュール版="conversation-state-v0.1",
            入力=before,
            出力={
                "新経路": state.直前経路,
                "新追跡ID": state.直前追跡ID,
                "履歴件数": len(state.履歴),
                "ニュース件数": len(state.直前ニュース),
            },
        )
        record = audit.確定(最終応答=response, 最終状態=最終状態)
        return チャット応答(response, record.追跡ID, record.ルートハッシュ, route, 最終状態)
