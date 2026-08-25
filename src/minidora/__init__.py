from .模型 import (
    LLM成立規定リポジトリ,
    LLM成立規定参照コミット,
    LLM成立規定版,
    LLM成立意味区別,
    言語状態,
    内部言語状態,
    文脈付き言語状態,
    成立候補,
    関係寄与,
    成立差,
    模型結果,
    言語対応,
    模型関係,
    関係規則,
    意味連続関係,
    MINIDORA模型核,
    標準模型核,
)
from .計算中間表現 import (
    計算中間表現版,
    計算値種別,
    計算値,
    計算作用,
    計算命令,
    計算中間表現,
    計算履歴,
    計算実行結果,
)
from .計算実行境界 import 計算実行境界版, 計算実行境界, 標準計算実行境界
from .命令計算降下 import 命令計算降下
from .HDS計算降下 import HDS計算降下
from .計算実行器 import 計算実行器, 実行文脈
from .layer0 import (
    Layer0,
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
from .hds_compiler_v1 import 公開HDSコンパイラ方針, 公開HDSコンパイラ
from .hds_compiler_failure_bank import HDS失敗署名Bank
from .hds_compiler_records import (
    HDS監査状態,
    HDS原理段階,
    HDS認知世界断片,
    HDS監査項目,
    HDS監査要求,
    HDS原理探索要求,
    HDS保持契約,
    HDSCompiler成果,
)
from .hds_compiler_records_v1_1 import (
    HDS失敗署名状態,
    HDS状態ノード,
    HDS遷移辺,
    HDS状態遷移図,
    HDS暗黙知記録,
    HDS失敗署名候補,
    HDSチェックリスト項目,
    HDS認知世界差分,
    HDS監査参照候補,
)
from .hds_compiler_records_v1_2 import (
    HDS改善対象,
    HDS失敗観測,
    HDS失敗署名記録,
    HDS抽出規則改善候補,
    HDS失敗署名BankSnapshot,
)
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
from .言語基底 import 言語基底版, 文字知識, 語彙知識, 言語基底P, 標準言語基底P
from .runtime import ミニドラ, 要求, 結果

__all__ = [
    "LLM成立規定リポジトリ", "LLM成立規定参照コミット", "LLM成立規定版", "LLM成立意味区別",
    "言語状態", "内部言語状態", "文脈付き言語状態", "成立候補", "関係寄与", "成立差", "模型結果",
    "言語対応", "模型関係", "関係規則", "意味連続関係", "MINIDORA模型核", "標準模型核",
    "計算中間表現版", "計算値種別", "計算値", "計算作用", "計算命令", "計算中間表現", "計算履歴", "計算実行結果",
    "計算実行境界版", "計算実行境界", "標準計算実行境界", "命令計算降下", "HDS計算降下",
    "計算実行器", "Layer0", "実行文脈",
    "LAYER0正本リポジトリ", "LAYER0参照コミット", "LAYER0仕様版", "LAYER0機能責任",
    "主体主幹", "主体状態", "主体更新提案", "主体整合結果", "主体更新記録",
    "参照供給器", "参照記録", "固定参照供給器", "複合参照供給器", "参照矛盾数",
    "OpenAlex参照供給器", "Wikipedia参照供給器", "EuropePMC参照供給器", "Crossref参照供給器", "一般知識参照供給器",
    "作用", "命令", "手順",
    "実行状態", "採否結果", "採否",
    "値状態", "HDS座標", "HDS関係", "HDS残差", "HDS意味作用", "HDS実行核", "HDSIR",
    "HDS文脈", "HDSコンパイラProtocol", "HDS独立コンパイル", "公開HDSコンパイラ方針", "公開HDSコンパイラ",
    "HDS監査状態", "HDS原理段階", "HDS認知世界断片", "HDS監査項目", "HDS監査要求", "HDS原理探索要求", "HDS保持契約", "HDSCompiler成果",
    "HDS失敗署名状態", "HDS状態ノード", "HDS遷移辺", "HDS状態遷移図", "HDS暗黙知記録", "HDS失敗署名候補", "HDSチェックリスト項目", "HDS認知世界差分", "HDS監査参照候補",
    "HDS改善対象", "HDS失敗観測", "HDS失敗署名記録", "HDS抽出規則改善候補", "HDS失敗署名BankSnapshot", "HDS失敗署名Bank",
    "HDS候補証拠", "HDS調停済証拠", "HDS候補調停結果", "HDS候補横断調停",
    "HDS選択実行結果", "HDS選択問題", "HDS選択推論実行",
    "HDS知識投入結果", "HDSIR知識Adapter", "HDS証拠事実", "HDS証拠状態複製",
    "HDS探索方針", "HDS努力水準", "HDS探索方針選択",
    "HDS参照予算", "HDS参照予算選択", "HDS参照問合せ候補", "HDS参照検索",
    "HDSIR辞書化", "HDSIR復元",
    "Trinity記憶監査", "記憶主体", "HDS判断主体", "Trinity文脈系",
    "K3相当能力核", "K3能力結果", "HDS候補診断", "HDSK3結果", "HDSIRネイティブAdapter", "run_k3_equivalence_benchmark",
    "自然言語器", "言語計画",
    "言語基底版", "文字知識", "語彙知識", "言語基底P", "標準言語基底P",
    "ミニドラ", "要求", "結果",
]
