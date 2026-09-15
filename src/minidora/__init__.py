from __future__ import annotations

from collections.abc import Sequence
from importlib import import_module
import sys

# 公開APIは保持し、実体は要求された時だけ読む。plain importで旧K3/HDS/HTTP/主体を起動しない。
_公開経路 = {
    'Crossref参照供給器': ('Crossref参照', 'Crossref参照供給器'),
    'EuropePMC参照供給器': ('EuropePMC参照', 'EuropePMC参照供給器'),
    'HDSCompiler成果': ('HDS構文化記録', 'HDSCompiler成果'),
    'HDSIR': ('HDS中間表現', 'HDSIR'),
    'HDSIRネイティブAdapter': ('K3_HDSネイティブ', 'HDSIRネイティブAdapter'),
    'HDSIR復元': ('HDS再生', 'HDSIR復元'),
    'HDSIR知識Adapter': ('HDS資料K', 'HDSIR知識Adapter'),
    'HDSIR辞書化': ('HDS再生', 'HDSIR辞書化'),
    'HDSK3結果': ('K3_HDSネイティブ', 'HDSK3結果'),
    'HDSコンパイラProtocol': ('HDS適合器', 'HDSコンパイラProtocol'),
    'HDSコンパイラパイプライン版': ('HDS構文化処理系列_v1_4', 'HDSコンパイラパイプライン版'),
    'HDSコンパイル束': ('HDS構文化器_v1', 'HDSコンパイル束'),
    'HDSチェックリスト項目': ('HDS構文化記録_v1_1', 'HDSチェックリスト項目'),
    'HDS一時証拠統合': ('HDS作業状態', 'HDS一時証拠統合'),
    'HDS作業Checkpoint': ('HDS作業状態', 'HDS作業Checkpoint'),
    'HDS作業状態': ('HDS作業状態', 'HDS作業状態'),
    'HDS作業状態構築': ('HDS作業状態', 'HDS作業状態構築'),
    'HDS作業統計': ('HDS作業状態', 'HDS作業統計'),
    'HDS作業関係': ('HDS作業状態', 'HDS作業関係'),
    'HDS作用差分構造': ('HDS構文化記録_v1_3', 'HDS作用差分構造'),
    'HDS作用差分構造生成': ('HDS構文化作用差分', 'HDS作用差分構造生成'),
    'HDS作用種別': ('hds統合判断主体', 'HDS作用種別'),
    'HDS作用要求': ('hds統合判断主体', 'HDS作用要求'),
    'HDS作用記録': ('HDS構文化記録_v1_3', 'HDS作用記録'),
    'HDS保持契約': ('HDS構文化記録', 'HDS保持契約'),
    'HDS候補共同状態更新': ('HDS作業状態', 'HDS候補共同状態更新'),
    'HDS候補共同項目': ('HDS作業状態', 'HDS候補共同項目'),
    'HDS候補横断調停': ('HDS候補再照合', 'HDS候補横断調停'),
    'HDS候補診断': ('K3_HDSネイティブ', 'HDS候補診断'),
    'HDS候補証拠': ('HDS候補再照合', 'HDS候補証拠'),
    'HDS候補調停結果': ('HDS候補再照合', 'HDS候補調停結果'),
    'HDS判断主体': ('トリニティ文脈', 'HDS判断主体'),
    'HDS努力水準': ('HDS探索方針', 'HDS努力水準'),
    'HDS原理探索要求': ('HDS構文化記録', 'HDS原理探索要求'),
    'HDS原理段階': ('HDS構文化記録', 'HDS原理段階'),
    'HDS参照予算': ('HDS参照', 'HDS参照予算'),
    'HDS参照予算選択': ('HDS参照', 'HDS参照予算選択'),
    'HDS参照問合せ候補': ('HDS参照', 'HDS参照問合せ候補'),
    'HDS参照検索': ('HDS参照', 'HDS参照検索'),
    'HDS失敗署名Bank': ('HDS構文化失敗集', 'HDS失敗署名Bank'),
    'HDS失敗署名BankSnapshot': ('HDS構文化記録_v1_2', 'HDS失敗署名BankSnapshot'),
    'HDS失敗署名候補': ('HDS構文化記録_v1_1', 'HDS失敗署名候補'),
    'HDS失敗署名状態': ('HDS構文化記録_v1_1', 'HDS失敗署名状態'),
    'HDS失敗署名記録': ('HDS構文化記録_v1_2', 'HDS失敗署名記録'),
    'HDS失敗観測': ('HDS構文化記録_v1_2', 'HDS失敗観測'),
    'HDS実行核': ('HDS中間表現', 'HDS実行核'),
    'HDS寄与Gate再照合': ('HDS作業状態', 'HDS寄与Gate再照合'),
    'HDS座標': ('HDS中間表現', 'HDS座標'),
    'HDS後続利用記録': ('HDS構文化記録_v1_3', 'HDS後続利用記録'),
    'HDS意味IR化': ('HDS構文化処理系列_v1_4', 'HDS意味IR化'),
    'HDS意味作用': ('HDS中間表現', 'HDS意味作用'),
    'HDS意味専用計画器': ('HDS構文化処理系列_v1_4', 'HDS意味専用計画器'),
    'HDS抽出規則改善候補': ('HDS構文化記録_v1_2', 'HDS抽出規則改善候補'),
    'HDS探索方針': ('HDS探索方針', 'HDS探索方針'),
    'HDS探索方針選択': ('HDS探索方針', 'HDS探索方針選択'),
    'HDS改善対象': ('HDS構文化記録_v1_2', 'HDS改善対象'),
    'HDS文脈': ('HDS適合器', 'HDS文脈'),
    'HDS暗黙知記録': ('HDS構文化記録_v1_1', 'HDS暗黙知記録'),
    'HDS残差': ('HDS中間表現', 'HDS残差'),
    'HDS状態ノード': ('HDS構文化記録_v1_1', 'HDS状態ノード'),
    'HDS状態差記録': ('HDS構文化記録_v1_3', 'HDS状態差記録'),
    'HDS状態遷移図': ('HDS構文化記録_v1_1', 'HDS状態遷移図'),
    'HDS独立コンパイル': ('HDS適合器', 'HDS独立コンパイル'),
    'HDS監査参照候補': ('HDS構文化記録_v1_1', 'HDS監査参照候補'),
    'HDS監査状態': ('HDS構文化記録', 'HDS監査状態'),
    'HDS監査要求': ('HDS構文化記録', 'HDS監査要求'),
    'HDS監査項目': ('HDS構文化記録', 'HDS監査項目'),
    'HDS知識投入結果': ('HDS資料K', 'HDS知識投入結果'),
    'HDS計算コンパイル成果': ('HDS構文化器_v1', 'HDS計算コンパイル成果'),
    'HDS計算降下': ('HDS計算降下', 'HDS計算降下'),
    'HDS計算降下バックエンド': ('HDS構文化処理系列_v1_4', 'HDS計算降下バックエンド'),
    'HDS証拠事実': ('HDS資料K', 'HDS証拠事実'),
    'HDS証拠状態複製': ('HDS資料K', 'HDS証拠状態複製'),
    'HDS認知世界差分': ('HDS構文化記録_v1_1', 'HDS認知世界差分'),
    'HDS認知世界断片': ('HDS構文化記録', 'HDS認知世界断片'),
    'HDS調停済証拠': ('HDS候補再照合', 'HDS調停済証拠'),
    'HDS遷移辺': ('HDS構文化記録_v1_1', 'HDS遷移辺'),
    'HDS選択問題': ('HDS選択実行系', 'HDS選択問題'),
    'HDS選択実行結果': ('HDS選択実行系', 'HDS選択実行結果'),
    'HDS選択推論実行': ('HDS選択実行系', 'HDS選択推論実行'),
    'HDS関係': ('HDS中間表現', 'HDS関係'),
    'HDS駆動ミニドラ': ('実行系_HDS_v1', 'HDS駆動ミニドラ'),
    'HDS駆動選択実行': ('hds統合実行系', 'HDS駆動選択実行'),
    'HDS駆動選択結果': ('hds統合実行系', 'HDS駆動選択結果'),
    'K3相当能力核': ('K3機能', 'K3相当能力核'),
    'K3能力結果': ('K3機能', 'SystemResult'),
    'LAYER0仕様版': ('第0層', 'LAYER0仕様版'),
    'LAYER0参照コミット': ('第0層', 'LAYER0参照コミット'),
    'LAYER0機能責任': ('第0層', 'LAYER0機能責任'),
    'LAYER0正本リポジトリ': ('第0層', 'LAYER0正本リポジトリ'),
    'Layer0': ('第0層', 'Layer0'),
    'MINIDORAHDS判断主体': ('hds統合判断主体', 'MINIDORAHDS判断主体'),
    'MINIDORA認知世界': ('hds統合判断主体', 'MINIDORA認知世界'),
    'OpenAlex参照供給器': ('HTTP参照', 'OpenAlex参照供給器'),
    'Trinity文脈系': ('トリニティ文脈', 'Trinity文脈系'),
    'Trinity記憶監査': ('トリニティ文脈', 'Trinity記憶監査'),
    'Wikipedia参照供給器': ('HTTP参照', 'Wikipedia参照供給器'),
    'run_k3_equivalence_benchmark': ('K3評価', 'run_k3_equivalence_benchmark'),
    'ミニドラ': ('実行系', 'ミニドラ'),
    '一般知識参照供給器': ('標準参照', '一般知識参照供給器'),
    '主体主幹': ('主体', '主体主幹'),
    '主体整合結果': ('主体', '主体整合結果'),
    '主体更新提案': ('主体', '主体更新提案'),
    '主体更新記録': ('主体', '主体更新記録'),
    '主体状態': ('主体', '主体状態'),
    '作用': ('命令', '作用'),
    '値状態': ('HDS中間表現', '値状態'),
    '公開HDSコンパイラ': ('HDS構文化器_v1', '公開HDSコンパイラ'),
    '公開HDSコンパイラ方針': ('HDS構文化器_v1', '公開HDSコンパイラ方針'),
    '参照供給器': ('参照', '参照供給器'),
    '参照矛盾数': ('参照', '参照矛盾数'),
    '参照記録': ('参照', '参照記録'),
    '命令': ('命令', '命令'),
    '命令計算降下': ('命令計算降下', '命令計算降下'),
    '固定参照供給器': ('参照', '固定参照供給器'),
    '実行文脈': ('計算実行器', '実行文脈'),
    '実行状態': ('採否', '実行状態'),
    '意味列': ('言語構造', '意味列'),
    '手順': ('命令', '手順'),
    '採否': ('採否', '採否'),
    '採否結果': ('採否', '採否結果'),
    '文字知識': ('言語基底', '文字知識'),
    '標準言語基底P': ('言語基底', '標準言語基底P'),
    '標準計算実行境界': ('計算実行境界', '標準計算実行境界'),
    '結果': ('実行系', '結果'),
    '自然言語器': ('言語', '自然言語器'),
    '複合参照供給器': ('参照', '複合参照供給器'),
    '要求': ('実行系', '要求'),
    '規模測定': ('規模測定', '規模測定'),
    '規模測定版': ('規模測定', '規模測定版'),
    '規模測定結果': ('規模測定', '規模測定結果'),
    '言語基底P': ('言語基底', '言語基底P'),
    '言語基底版': ('言語基底', '言語基底版'),
    '言語計画': ('言語', '言語計画'),
    '言語関係抽出': ('言語構造', '言語関係抽出'),
    '言語関係構造': ('言語構造', '言語関係構造'),
    '計算中間表現': ('計算中間表現', '計算中間表現'),
    '計算中間表現版': ('計算中間表現', '計算中間表現版'),
    '計算作用': ('計算中間表現', '計算作用'),
    '計算値': ('計算中間表現', '計算値'),
    '計算値種別': ('計算中間表現', '計算値種別'),
    '計算命令': ('計算中間表現', '計算命令'),
    '計算実行器': ('計算実行器', '計算実行器'),
    '計算実行境界': ('計算実行境界', '計算実行境界'),
    '計算実行境界版': ('計算実行境界', '計算実行境界版'),
    '計算実行結果': ('計算中間表現', '計算実行結果'),
    '計算履歴': ('計算中間表現', '計算履歴'),
    '記憶主体': ('トリニティ文脈', '記憶主体'),
    '語彙知識': ('言語基底', '語彙知識'),
}
_互換ワイルドカード = ("模型_v05",)

def _ロード済み公開名を正規化() -> None:
    """submodule importがpackage属性へ置いた同名moduleを公開API実体へ戻す。"""
    for public_name, (module_name, source_name) in _公開経路.items():
        loaded = sys.modules.get(f"{__name__}.{module_name}")
        if loaded is None or not hasattr(loaded, source_name):
            continue
        current = globals().get(public_name)
        if current is loaded or public_name not in globals():
            globals()[public_name] = getattr(loaded, source_name)

def __getattr__(name: str):
    route = _公開経路.get(name)
    if route is not None:
        module_name, source_name = route
        module = import_module(f".{module_name}", __name__)
        value = getattr(module, source_name)
        globals()[name] = value
        _ロード済み公開名を正規化()
        return globals().get(name, value)
    for module_name in _互換ワイルドカード:
        module = import_module(f".{module_name}", __name__)
        _ロード済み公開名を正規化()
        if name in getattr(module, "__all__", ()) and hasattr(module, name):
            value = getattr(module, name)
            globals()[name] = value
            return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

class _遅延公開名(Sequence):
    _cache: tuple[str, ...] | None = None
    def _names(self) -> tuple[str, ...]:
        if self._cache is None:
            names = set(_公開経路)
            for module_name in _互換ワイルドカード:
                module = import_module(f".{module_name}", __name__)
                _ロード済み公開名を正規化()
                names.update(getattr(module, "__all__", ()))
            self._cache = tuple(sorted(names))
        return self._cache
    def __len__(self): return len(self._names())
    def __getitem__(self, index): return self._names()[index]
    def __iter__(self): return iter(self._names())

__all__ = _遅延公開名()

def __dir__():
    return sorted(set(globals()) | set(_公開経路))
