from .layer0 import (
    Layer0,
    実行文脈,
    LAYER0正本リポジトリ,
    LAYER0参照コミット,
    LAYER0仕様版,
    LAYER0機能責任,
)
from .主体 import 主体主幹, 主体状態, 主体更新提案, 主体整合結果, 主体更新記録
from .参照 import 参照供給器, 参照記録, 固定参照供給器, 複合参照供給器, 参照矛盾数
from .http_reference import OpenAlex参照供給器, Wikipedia参照供給器
from .europe_pmc_reference import EuropePMC参照供給器
from .crossref_reference import Crossref参照供給器
from .standard_reference import 一般知識参照供給器
from .命令 import 作用, 命令, 手順
from .採否 import 実行状態, 採否結果, 採否
from .hds_ir import 値状態, HDS座標, HDS関係, HDS残差, HDS意味作用, HDS実行核, HDSIR
from .hds_adapter import HDS文脈, HDSコンパイラProtocol, HDS独立コンパイル
from .hds_candidate_reconcile import HDS候補証拠, HDS調停済証拠, HDS候補調停結果, HDS候補横断調停
from .hds_choice_runtime import HDS選択実行結果, HDS選択問題, HDS選択推論実行
from .hds_data_k import HDS知識投入結果, HDSIR知識Adapter, HDS証拠事実, HDS証拠状態複製
from .hds_effort import HDS探索方針, HDS努力水準, HDS探索方針選択
from .hds_reference import HDS参照予算, HDS参照予算選択, HDS参照問合せ候補, HDS参照検索
from .hds_replay import HDSIR辞書化, HDSIR復元
from .trinity_context import Trinity記憶監査, 記憶主体, HDS判断主体, Trinity文脈系
from .k3_functional import K3相当能力核, SystemResult as K3能力結果
from .k3_hds_native import HDS候補診断, HDSK3結果, HDSIRネイティブAdapter
from .k3_benchmark import run_k3_equivalence_benchmark
from .言語 import 自然言語器, 言語計画
from .runtime import ミニドラ, 要求, 結果

__all__ = [
    "Layer0", "実行文脈",
    "LAYER0正本リポジトリ", "LAYER0参照コミット", "LAYER0仕様版", "LAYER0機能責任",
    "主体主幹", "主体状態", "主体更新提案", "主体整合結果", "主体更新記録",
    "参照供給器", "参照記録", "固定参照供給器", "複合参照供給器", "参照矛盾数",
    "OpenAlex参照供給器", "Wikipedia参照供給器", "EuropePMC参照供給器", "Crossref参照供給器", "一般知識参照供給器",
    "作用", "命令", "手順",
    "実行状態", "採否結果", "採否",
    "値状態", "HDS座標", "HDS関係", "HDS残差", "HDS意味作用", "HDS実行核", "HDSIR",
    "HDS文脈", "HDSコンパイラProtocol", "HDS独立コンパイル",
    "HDS候補証拠", "HDS調停済証拠", "HDS候補調停結果", "HDS候補横断調停",
    "HDS選択実行結果", "HDS選択問題", "HDS選択推論実行",
    "HDS知識投入結果", "HDSIR知識Adapter", "HDS証拠事実", "HDS証拠状態複製",
    "HDS探索方針", "HDS努力水準", "HDS探索方針選択",
    "HDS参照予算", "HDS参照予算選択", "HDS参照問合せ候補", "HDS参照検索",
    "HDSIR辞書化", "HDSIR復元",
    "Trinity記憶監査", "記憶主体", "HDS判断主体", "Trinity文脈系",
    "K3相当能力核", "K3能力結果", "HDS候補診断", "HDSK3結果", "HDSIRネイティブAdapter", "run_k3_equivalence_benchmark",
    "自然言語器", "言語計画",
    "ミニドラ", "要求", "結果",
]
