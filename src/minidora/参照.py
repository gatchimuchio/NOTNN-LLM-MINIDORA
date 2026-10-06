from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import re
import time
import unicodedata
from dataclasses import dataclass, replace
from threading import RLock
from email.utils import parsedate_to_datetime
from datetime import timezone
from hashlib import sha256
import json
from typing import Any, Iterable, Protocol


@dataclass(frozen=True, slots=True)
class 参照記録:
    識別子: str
    対象: str
    内容: str
    由来: str
    供給器: str
    信頼: float = 1.0
    意味キー: str | None = None
    値: Any = None
    時点: str | None = None
    範囲: str | None = None
    条件: tuple[tuple[str, str], ...] = ()
    意味確定: bool = False
    # 現在の作業版と旧観測版を分ける。旧版は独立票として数えない。
    旧版: tuple["参照記録", ...] = ()
    観測経路履歴: tuple[tuple[tuple[str, str], ...], ...] = ()

    @property
    def 表示値(self) -> Any:
        return self.値 if self.意味キー is not None else self.内容


class 参照供給器(Protocol):
    名称: str

    def 検索(self, 問合せ: str, 上限: int = 8) -> tuple[参照記録, ...]: ...


@dataclass(frozen=True, slots=True)
class 参照取得診断:
    問合せ: str
    供給器: str
    状態: str
    取得件数: int
    試行回数: int = 1
    エラー: str | None = None
    子診断: tuple["参照取得診断", ...] = ()
    HTTP状態: int | None = None
    再試行可能epoch: float | None = None
    実取得回数: int = 0
    再利用: bool = False
    延期理由: str | None = None


def _応答制限(例外=None, 診断=None):
    """HTTP 429とRetry-Afterを分離する。指定のない待機時間を推測しない。"""
    状態 = getattr(例外, "code", None) if 例外 is not None else 診断.HTTP状態
    文 = str(例外) if 例外 is not None else str(診断.エラー or "")
    if 状態 is None and re.search(r"(?:HTTP(?:Error| Error)?[ :]+|status(?:_code)?[=: ]+)429\b", 文, re.I):
        状態 = 429
    再試行 = 診断.再試行可能epoch if 診断 is not None else None
    ヘッダ = getattr(例外, "headers", None)
    値 = ヘッダ.get("Retry-After") if ヘッダ is not None else None
    if 値 is not None:
        try:
            if str(値).strip().isdigit():
                再試行 = time.time() + int(str(値).strip())
            else:
                時刻 = parsedate_to_datetime(str(値))
                if 時刻.tzinfo is None: 時刻 = 時刻.replace(tzinfo=timezone.utc)
                再試行 = 時刻.timestamp()
        except (ValueError, TypeError, OverflowError):
            再試行 = None
    return 状態, 再試行


def 参照検索を診断(
    供給器: 参照供給器, 問合せ: str, 上限: int = 8, *,
    最大試行: int = 3, 再試行待機秒: float = 0.05,
    締切epoch: float | None = None,
) -> tuple[tuple[参照記録, ...], 参照取得診断]:
    """空・部分成功・取得障害・制限応答を分け、成功済み成分を再取得しない。"""
    if type(最大試行) is not int or 最大試行 < 1:
        raise ValueError("最大試行は1以上の整数が必要")
    直接診断 = getattr(供給器, "検索診断", None)
    名称 = str(getattr(供給器, "名称", type(供給器).__name__))
    既存 = ()
    最終 = 参照取得診断(str(問合せ), 名称, "失敗", 0, 0, "未実行")
    実取得 = 0
    for 試行 in range(1, 最大試行 + 1):
        if 締切epoch is not None and time.time() >= 締切epoch:
            return 既存, replace(最終, 状態="縮退" if 既存 else "失敗",
                実取得回数=実取得, 延期理由="共通締切到達")
        try:
            if callable(直接診断):
                記録群, 診断 = 直接診断(問合せ, 上限)
                if not isinstance(診断, 参照取得診断): raise TypeError("検索診断の型不正")
                実取得 += 診断.実取得回数 if 診断.再利用 or 診断.実取得回数 else 1
                最終 = replace(診断, 試行回数=max(診断.試行回数, 試行))
            else:
                記録群 = tuple(供給器.検索(問合せ, 上限))
                実取得 += 1
                誤り = getattr(供給器, "最後のエラー", None)
                最終 = 参照取得診断(str(問合せ), 名称,
                    "縮退" if 誤り and 記録群 else "失敗" if 誤り else "取得" if 記録群 else "空",
                    len(記録群), 試行, str(誤り) if 誤り else None)
            記録群 = tuple(記録群)
            if any(not isinstance(x, 参照記録) for x in 記録群): raise TypeError("参照記録型不正")
            既存 = 参照全保持を統合(既存, 記録群)
            状態, 再試行 = _応答制限(診断=最終)
            最終 = replace(最終, HTTP状態=状態, 再試行可能epoch=再試行,
                           取得件数=len(既存), 実取得回数=実取得)
            # 完全取得・空は確定。通常の部分成功も保持して返す。
            # ただし429を伴う部分成功は旧43点経路と同じく有限再試行し、
            # 一覧取得だけ成功・detail証拠欠落を「完了」へ昇格させない。
            if 最終.状態 in {"取得", "空"} or bool(getattr(供給器, "診断内再試行", False)):
                return 既存, 最終
            if 既存 and 最終.HTTP状態 != 429:
                return 既存, 最終
        except Exception as 例外:
            実取得 += 1
            状態, 再試行 = _応答制限(例外=例外)
            最終 = 参照取得診断(str(問合せ), 名称, "縮退" if 既存 else "失敗",
                len(既存), 試行, type(例外).__name__ + ": " + str(例外),
                HTTP状態=状態, 再試行可能epoch=再試行, 実取得回数=実取得)
        if 最終.HTTP状態 == 429 and 最終.再試行可能epoch is not None:
            # Retry-Afterが明示された場合は推測せず、その時点まで延期する。
            return 既存, replace(最終, 延期理由="供給器の制限解除待ち")
        if 最終.HTTP状態 == 429 and 最終.再試行可能epoch is None and 試行 >= 最大試行:
            # 解除時点が無い429は恒久停止へ昇格させない。同一queryだけ有限再試行し、
            # 上限到達後に診断として残す。次回の同一query再利用は複合供給器側が担う。
            return 既存, replace(最終, 延期理由="制限解除時点未提示。有限再試行上限到達")
        if 試行 < 最大試行 and 再試行待機秒 > 0:
            待機 = float(再試行待機秒) * 試行
            if 締切epoch is not None and time.time() + 待機 >= 締切epoch:
                return 既存, replace(最終, 延期理由="再試行待機が共通締切を越える")
            time.sleep(待機)
    return 既存, 最終


def _検索語(問合せ: str) -> set[str]:
    text = unicodedata.normalize("NFKC", 問合せ).casefold().strip()
    if not text:
        return set()
    text = re.sub(r"[\s、。,.!?！？「」『』（）()【】\[\]：:]+", " ", text)
    text = re.sub(
        r"(?<=[0-9a-z一-龯ぁ-んァ-ン])(?:について|から|まで|より|ので|の|は|が|を|に|で|と|へ|や|も)(?=[0-9a-z一-龯ぁ-んァ-ン])",
        " ",
        text,
    )
    return {part for part in text.split() if part}


def 参照矛盾数(記録群: Iterable[参照記録]) -> int:
    groups: dict[
        tuple[str, str, str | None, str | None, tuple[tuple[str, str], ...]],
        set[str],
    ] = {}
    for record in 記録群:
        if record.意味キー is None or not record.意味確定:
            continue
        key = (
            record.対象,
            record.意味キー,
            record.時点,
            record.範囲,
            tuple(record.条件),
        )
        groups.setdefault(key, set()).add(repr(record.値))
    return sum(1 for values in groups.values() if len(values) > 1)


class 固定参照供給器:
    並列安全 = True

    def __init__(self, 記録群: Iterable[参照記録], 名称: str = "固定資料") -> None:
        self.名称 = 名称
        self._記録群 = tuple(記録群)

    def 検索(self, 問合せ: str, 上限: int = 8) -> tuple[参照記録, ...]:
        語 = _検索語(問合せ)
        if not 語:
            return self._記録群[:上限]
        採点済み: list[tuple[int, 参照記録]] = []
        for 記録 in self._記録群:
            意味面 = " ".join(
                str(value)
                for value in (
                    記録.対象,
                    記録.意味キー or "",
                    記録.値 if 記録.意味キー is not None else "",
                    記録.時点 or "",
                    記録.範囲 or "",
                    記録.内容,
                )
            )
            本文 = unicodedata.normalize("NFKC", 意味面).casefold()
            点 = sum(1 for 字句 in 語 if 字句 in 本文)
            if 点:
                採点済み.append((点, 記録))
        採点済み.sort(key=lambda x: (-x[0], x[1].識別子))
        return tuple(record for _, record in 採点済み[:上限])


def _記録品質(record: 参照記録) -> tuple[int, float, int]:
    return (1 if record.意味確定 else 0, float(record.信頼), len(str(record.内容)))


def _内容版(記録):
    # 記録内部の問い合わせ経路は意味内容から分離する。
    条件 = tuple((k, v) for k, v in 記録.条件 if not str(k).startswith(("hds_", "observed_by_")))
    from .コア.値 import 署名
    return 署名((記録.識別子, 記録.対象, 記録.内容, 記録.由来, 記録.意味キー,
                記録.値, 記録.時点, 記録.範囲, 条件, 記録.意味確定))


def _観測版(記録):
    """観測内容の版を識別する。追跡用provider印は同一性へ混ぜない。"""
    from .コア.値 import 署名
    条件 = tuple((k, v) for k, v in 記録.条件 if not str(k).startswith("observed_by_"))
    return 署名((_内容版(記録), 記録.供給器, float(記録.信頼), 条件))


def _平坦観測(記録: 参照記録) -> 参照記録:
    return replace(記録, 旧版=())


def _同一情報源統合(old: 参照記録, new: 参照記録) -> 参照記録:
    """全保持用。現在版と観測履歴を分け、異なる提供元を投票へ使わない。"""
    旧現, 新観測 = _平坦観測(old), _平坦観測(new)
    # 完全に同じ観測の再投入は何も変更しない。履歴も増やさない。
    if _観測版(旧現) == _観測版(新観測):
        return old
    同一提供元 = str(旧現.供給器) == str(新観測.供給器)
    if 同一提供元:
        # 同じ情報源の訂正は本文長・信頼の大小にかかわらず新観測を現版にする。
        現 = 新観測
        候補旧版 = (*old.旧版, 旧現, *new.旧版)
        現版 = _観測版(現)
        版群 = {}
        for 項 in 候補旧版:
            平坦 = _平坦観測(項)
            鍵 = _観測版(平坦)
            if 鍵 != 現版:
                版群[鍵] = 平坦
    else:
        # 別providerの同一IDは、現在版を書き換えず独立観測として全て履歴へ保持する。
        現 = 旧現
        版群 = {}
        for 項 in (*old.旧版, 旧現, *new.旧版, 新観測):
            平坦 = _平坦観測(項)
            版群[_観測版(平坦)] = 平坦
    経路 = tuple(dict.fromkeys((*old.観測経路履歴, old.条件,
                              *new.観測経路履歴, new.条件)))
    return replace(現, 旧版=tuple(版群.values()), 観測経路履歴=経路)


def _作業窓統合(old: 参照記録, new: 参照記録) -> 参照記録:
    """今回の演算窓用。意味条件は現版、query/観測経路は全観測から保持する。"""
    旧現, 新観測 = _平坦観測(old), _平坦観測(new)
    現 = 新観測 if _記録品質(新観測) > _記録品質(旧現) else 旧現
    観測群 = (*old.旧版, 旧現, *new.旧版, 新観測)

    def 経路条件(条件):
        return str(条件[0]).startswith(("hds_query_", "hds_observation_", "observed_by_"))

    # 温度・時点等の意味条件を別観測から混ぜない。一方、同じ資料がどの候補queryで
    # 観測されたかは真偽票ではなく経路情報なので、作業窓でも落とさず併合する。
    条件 = [x for x in 現.条件 if not 経路条件(x)]
    for 項 in 観測群:
        for 条件項 in 項.条件:
            if 経路条件(条件項) and 条件項 not in 条件:
                条件.append(条件項)
        印 = ("observed_by_provider", str(項.供給器))
        if 印 not in 条件:
            条件.append(印)
    # 作業窓の選択と全保持を分離する。旧版には生観測を残す。
    履歴版 = {}
    for 項 in 観測群:
        平坦 = _平坦観測(項)
        if _観測版(平坦) != _観測版(現):
            履歴版[_観測版(平坦)] = 平坦
    return replace(現, 条件=tuple(条件), 旧版=tuple(履歴版.values()),
        観測経路履歴=tuple(dict.fromkeys((*old.観測経路履歴, old.条件,
                                          *new.観測経路履歴, new.条件))))


class 参照保持容量超過(RuntimeError):
    def __init__(self, 記録群, 上限):
        super().__init__(f"参照保持容量超過: {len(記録群)} > {上限}。記録は例外へ保持")
        self.記録群, self.上限 = tuple(記録群), 上限


def 参照全保持を統合(既存, 追加, *, 最大件数=None):
    """保持と今回読む量を分離する。容量境界で無言に末尾を捨てない。"""
    if 最大件数 is not None and (type(最大件数) is not int or 最大件数 < 1):
        raise ValueError("保持容量は正整数または未指定")
    記録群 = tuple(既存) + tuple(追加)
    結果, 位置 = [], {}
    for 記録 in 記録群:
        if not isinstance(記録, 参照記録): raise TypeError("参照記録が必要")
        鍵 = str(記録.識別子).strip()
        if not 鍵:
            鍵 = "匿名:" + _内容版(記録)
        if 鍵 in 位置:
            結果[位置[鍵]] = _同一情報源統合(結果[位置[鍵]], 記録)
        else:
            位置[鍵] = len(結果); 結果.append(記録)
    if 最大件数 is not None and len(結果) > 最大件数:
        raise 参照保持容量超過(結果, 最大件数)
    return tuple(結果)


def 参照記録群を統合(
    既存: Iterable[参照記録],
    追加: Iterable[参照記録],
    *,
    最大件数: int = 8192,
) -> tuple[参照記録, ...]:
    """観測済み参照を識別子単位で保持し、後続処理から再利用可能な記憶へ統合する。"""
    if type(最大件数) is not int or 最大件数 < 1:
        raise ValueError("参照記憶の最大件数は1以上の整数である必要がある")
    結果: list[参照記録] = []
    位置: dict[str, int] = {}
    for record in (*tuple(既存), *tuple(追加)):
        key = str(record.識別子).strip() or f"anonymous:{record.供給器}:{record.由来}:{len(結果)}"
        if key in 位置:
            結果[位置[key]] = _作業窓統合(結果[位置[key]], record)
            continue
        if len(結果) >= 最大件数:
            break
        位置[key] = len(結果)
        結果.append(record)
    return tuple(結果)


def 参照記録を経験記憶化(record: 参照記録) -> 参照記録:
    """問固有の検索経路印を落とし、観測内容と意味条件だけを後続経験へ残す。"""
    条件 = tuple(
        (str(key), str(value))
        for key, value in record.条件
        if not str(key).startswith(("hds_query_", "hds_observation_"))
    )
    return replace(record, 条件=条件, 観測経路履歴=tuple(dict.fromkeys((*record.観測経路履歴, record.条件))))


def 参照経験記憶を統合(
    既存: Iterable[参照記録],
    追加: Iterable[参照記録],
    *,
    最大件数: int = 8192,
) -> tuple[参照記録, ...]:
    return 参照全保持を統合(
        tuple(参照記録を経験記憶化(x) for x in 既存),
        tuple(参照記録を経験記憶化(x) for x in 追加),
        最大件数=最大件数,
    )


class 複合参照供給器:
    """複数Providerを並列取得し、Provider順を保ったround-robinで統合する。

    同一識別子は独立資料として二重計上せず、信頼度・本文量の高い記録へ品質統合する。
    外側のquery並列は無効化し、Provider内部並列だけを許可して診断の対応関係を固定する。
    """

    並列安全 = False
    診断内再試行 = True

    def __init__(
        self,
        *供給器群: 参照供給器,
        名称: str = "複合参照",
        並列: bool = True,
        最大並列: int = 4,
        最大再試行: int = 3,
        再試行待機秒: float = 0.05,
    ) -> None:
        self.名称 = 名称
        self._供給器群 = tuple(供給器群)
        self.並列 = bool(並列)
        self.最大並列 = max(1, int(最大並列))
        self.最大再試行 = max(1, int(最大再試行))
        self.再試行待機秒 = max(0.0, float(再試行待機秒))
        self.最後のエラー: tuple[tuple[str, str], ...] = ()
        self._取得済み = {}
        self._制限 = {}
        self._取得鎖 = RLock()
        self._全観測 = ()
        self.締切epoch = None

    @property
    def 全観測記録(self):
        with self._取得鎖: return self._全観測

    def 制限を再開(self, 供給器名, *, 理由):
        if not isinstance(理由, str) or not 理由.strip(): raise ValueError("制限再開の根拠が必要")
        with self._取得鎖:
            self._制限.pop(供給器名, None)


    def _取得(self, 供給器: 参照供給器, 問合せ: str, 上限: int) -> tuple[tuple[参照記録, ...], 参照取得診断]:
        名称 = str(getattr(供給器, "名称", type(供給器).__name__))
        鍵 = (id(供給器), str(問合せ), 上限, str(getattr(供給器, "観測版", "")))
        with self._取得鎖:
            既存 = self._取得済み.get(鍵)
            制限 = self._制限.get(名称)
        if 既存 is not None:
            記録, 診断 = 既存
            return 記録, replace(診断, 再利用=True, 実取得回数=0)
        if 制限 is not None:
            # Retry-Afterが明示された制限だけを供給器全体へ適用する。
            # 解除時点未提示の429は同一queryの再連打だけを取得済み鍵で止め、
            # 別queryまで無期限停止へ拡大しない。
            if 制限.再試行可能epoch is not None and time.time() < 制限.再試行可能epoch:
                return (), replace(制限, 問合せ=問合せ, 取得件数=0, 実取得回数=0, 再利用=True)
            with self._取得鎖: self._制限.pop(名称, None)
        記録, 診断 = 参照検索を診断(供給器, 問合せ, 上限,
            最大試行=self.最大再試行, 再試行待機秒=self.再試行待機秒, 締切epoch=self.締切epoch)
        with self._取得鎖:
            self._全観測 = 参照全保持を統合(self._全観測, 記録)
            if (診断.状態 in {"取得", "空"}
                    or (診断.HTTP状態 == 429 and 診断.再試行可能epoch is None)):
                self._取得済み[鍵] = (記録, 診断)
            if 診断.HTTP状態 == 429 and 診断.再試行可能epoch is not None:
                self._制限[名称] = 診断
        return 記録, 診断

    def 検索診断(self, 問合せ: str, 上限: int = 8) -> tuple[tuple[参照記録, ...], 参照取得診断]:
        if 上限 <= 0 or not self._供給器群:
            return (), 参照取得診断(str(問合せ), self.名称, "空", 0)

        pools: list[tuple[参照記録, ...]] = []
        診断群: list[参照取得診断] = []
        if self.並列 and len(self._供給器群) > 1:
            workers = min(self.最大並列, len(self._供給器群))
            with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="minidora-r") as executor:
                futures = [executor.submit(self._取得, 供給器, 問合せ, 上限) for 供給器 in self._供給器群]
                for future in futures:
                    try:
                        記録群, 診断 = future.result()
                    except Exception as exc:
                        記録群 = ()
                        診断 = 参照取得診断(
                            str(問合せ), "複合子供給器", "失敗", 0, 1, f"{type(exc).__name__}: {exc}"
                        )
                    pools.append(tuple(記録群))
                    診断群.append(診断)
        else:
            for 供給器 in self._供給器群:
                記録群, 診断 = self._取得(供給器, 問合せ, 上限)
                pools.append(tuple(記録群))
                診断群.append(診断)

        完全失敗診断 = tuple(x for x in 診断群 if x.状態 == "失敗")
        縮退診断 = tuple(x for x in 診断群 if x.状態 in {"失敗", "縮退"})
        self.最後のエラー = tuple((x.供給器, x.エラー or x.状態) for x in 縮退診断)

        結果: list[参照記録] = []
        index_by_id: dict[str, int] = {}
        depth = 0
        while True:
            progressed = False
            for pool in pools:
                if depth >= len(pool):
                    continue
                progressed = True
                record = pool[depth]
                existing = index_by_id.get(record.識別子)
                if existing is not None:
                    結果[existing] = _作業窓統合(結果[existing], record)
                    continue
                if len(結果) >= 上限:
                    continue
                index_by_id[record.識別子] = len(結果)
                結果.append(record)
            if not progressed:
                break
            depth += 1

        if 診断群 and len(完全失敗診断) == len(診断群):
            状態 = "失敗"
        elif 縮退診断:
            状態 = "縮退"
        else:
            状態 = "取得" if 結果 else "空"
        診断 = 参照取得診断(
            str(問合せ),
            self.名称,
            状態,
            len(結果),
            max((x.試行回数 for x in 診断群), default=1),
            None if not 縮退診断 else "; ".join(x.エラー or x.状態 for x in 縮退診断),
            tuple(診断群),
            実取得回数=sum(x.実取得回数 for x in 診断群),
            再利用=all(x.再利用 for x in 診断群),
            延期理由="; ".join(x.延期理由 for x in 診断群 if x.延期理由) or None,
        )
        return tuple(結果), 診断

    def 検索(self, 問合せ: str, 上限: int = 8) -> tuple[参照記録, ...]:
        return self.検索診断(問合せ, 上限)[0]