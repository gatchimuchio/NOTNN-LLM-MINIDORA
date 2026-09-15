from __future__ import annotations

from pathlib import Path
import io
import re
import tokenize

根 = Path(__file__).resolve().parents[1]


ソース移動 = {
    "src/minidora/Crossref参照.py": "src/minidora/Crossref参照.py",
    "src/minidora/EuropePMC参照.py": "src/minidora/EuropePMC参照.py",
    "src/minidora/HDS候補再照合.py": "src/minidora/HDS候補再照合.py",
    "src/minidora/HDS選択仮説.py": "src/minidora/HDS選択仮説.py",
    "src/minidora/HDS選択実行系_v24.py": "src/minidora/HDS選択実行系_v24.py",
    "src/minidora/HDS構文化処理系列_v1_3.py": "src/minidora/HDS構文化処理系列_v1_3.py",
    "src/minidora/HDS構文化記録_v1_1.py": "src/minidora/HDS構文化記録_v1_1.py",
    "src/minidora/HDS構文化記録_v1_2.py": "src/minidora/HDS構文化記録_v1_2.py",
    "src/minidora/HDS資料K.py": "src/minidora/HDS資料K.py",
    "src/minidora/HDS直接関係検証.py": "src/minidora/HDS直接関係検証.py",
    "src/minidora/HDS探索方針.py": "src/minidora/HDS探索方針.py",
    "src/minidora/HDS関係図推論.py": "src/minidora/HDS関係図推論.py",
    "src/minidora/HDS再生.py": "src/minidora/HDS再生.py",
    "src/minidora/HDS再生_capture.py": "src/minidora/HDS再生記録.py",
    "src/minidora/HDS再生_eval.py": "src/minidora/HDS再生評価.py",
    "src/minidora/HTTP参照.py": "src/minidora/HTTP参照.py",
    "src/minidora/K3評価.py": "src/minidora/K3評価.py",
    "src/minidora/K3機能.py": "src/minidora/K3機能.py",
    "src/minidora/K3生成.py": "src/minidora/K3生成.py",
    "src/minidora/K3_HDSネイティブ.py": "src/minidora/K3_HDSネイティブ.py",
    "src/minidora/第0層.py": "src/minidora/第0層.py",
    "src/minidora/実行系_HDS_v1.py": "src/minidora/実行系_HDS_v1.py",
    "src/minidora/実行系_v03.py": "src/minidora/実行系_v03.py",
}

ツール移動 = {
    "tools/模型核24修復_AB.py": "tools/模型核24修復_AB.py",
    "tools/GPQA再生記録.py": "tools/GPQA再生記録.py",
    "tools/GPQA科学専門能力再生.py": "tools/GPQA科学専門能力再生.py",
    "tools/HDS選択再生評価.py": "tools/HDS選択再生評価.py",
    "tools/HDS再生_ablation.py": "tools/HDS再生除去比較.py",
    "tools/HDS再生_benchmark.py": "tools/HDS再生評価.py",
    "tools/HDS再生_capture.py": "tools/HDS再生記録.py",
    "tools/HDS再生_compare.py": "tools/HDS再生比較.py",
}

試験移動 = {
    "tests/test_cli.py": "tests/test_コマンドライン.py",
    "tests/test_第0層.py": "tests/test_第0層.py",
}

既存互換入口 = (
    "tools/audit_projection_chain.py",
    "tools/benchmark.py",
    "tools/benchmark_formal.py",
    "tools/benchmark_formal_scientific_ab.py",
    "tools/benchmark_strict.py",
    "tools/glm_weight_manifest_discover.py",
    "tools/glm_weight_stream_audit.py",
    "tools/gpqa_measure_current.py",
    "tools/k3_hf_identity_inventory.py",
    "tools/k3_public_artifact_inventory.py",
    "tools/repository_consistency_check.py",
)

設計互換案内 = {
    "設計/10_HDS_Compiler_Architecture_v1.md": "10_HDS構文化器_構造_v1.md",
    "設計/11_HDS_Compiler_Architecture_v1_1.md": "11_HDS構文化器_構造_v1_1.md",
    "設計/12_HDS_Compiler_Architecture_v1_2.md": "12_HDS構文化器_構造_v1_2.md",
    "設計/26_HDS_Compiler_Pipeline_v1_3.md": "26_HDS構文化器_処理系列_v1_3.md",
    "設計/26_HDS_Compiler_Pipeline_v1_4.md": "26_HDS構文化器_処理系列_v1_4.md",
}

モジュール名置換 = {
    "Crossref参照": "Crossref参照",
    "EuropePMC参照": "EuropePMC参照",
    "HDS候補再照合": "HDS候補再照合",
    "HDS選択仮説": "HDS選択仮説",
    "HDS選択実行系_v24": "HDS選択実行系_v24",
    "HDS構文化処理系列_v1_3": "HDS構文化処理系列_v1_3",
    "HDS構文化記録_v1_1": "HDS構文化記録_v1_1",
    "HDS構文化記録_v1_2": "HDS構文化記録_v1_2",
    "HDS資料K": "HDS資料K",
    "HDS直接関係検証": "HDS直接関係検証",
    "HDS探索方針": "HDS探索方針",
    "HDS関係図推論": "HDS関係図推論",
    "HDS再生": "HDS再生",
    "HDS再生_capture": "HDS再生記録",
    "HDS再生_eval": "HDS再生評価",
    "HTTP参照": "HTTP参照",
    "K3評価": "K3評価",
    "K3機能": "K3機能",
    "K3生成": "K3生成",
    "K3_HDSネイティブ": "K3_HDSネイティブ",
    "第0層": "第0層",
    "実行系_HDS_v1": "実行系_HDS_v1",
    "実行系_v03": "実行系_v03",
}

ツール名置換 = {
    "模型核24修復_AB.py": "模型核24修復_AB.py",
    "GPQA再生記録.py": "GPQA再生記録.py",
    "GPQA科学専門能力再生.py": "GPQA科学専門能力再生.py",
    "HDS選択再生評価.py": "HDS選択再生評価.py",
    "HDS再生_ablation.py": "HDS再生除去比較.py",
    "HDS再生_benchmark.py": "HDS再生評価.py",
    "HDS再生_capture.py": "HDS再生記録.py",
    "HDS再生_compare.py": "HDS再生比較.py",
}

状態値置換 = {
    "原則暫定": "原則暫定",
    "作用閉包": "作用閉包",
    "構造化公開射影": "構造化公開射影",
    "全領域有効": "全領域有効",
    "部分構文化": "部分構文化",
    "意味保持": "意味保持",
    "未形成": "未形成",
    "影": "影",
    "パターン": "パターン",
    "機構候補": "機構候補",
    "原理候補": "原理候補",
    "標準関係": "標準関係",
    "形成済み関係": "形成済み関係",
    "一次能力作用": "一次能力作用",
}

識別子置換 = {
    "src/minidora/HDS構文化動態.py": {"_state_name": "_状態名"},
    "src/minidora/HDS構文化基礎.py": {"add_relation": "関係を追加"},
    "src/minidora/HDS構文化履歴.py": {"_relation_signature": "_関係署名"},
    "src/minidora/HDS監督選択実行系.py": {
        "_candidate_sig": "_候補署名", "supervisory_state": "監督状態",
        "run_action": "作用を実行", "final_result": "最終結果",
    },
    "src/minidora/HDS言語関係.py": {"add_relation": "関係を追加"},
    "src/minidora/HDS候補再照合.py": {"_collapse_by_source": "_情報源別に統合"},
    "src/minidora/HDS資料K.py": {
        "_source_confidence": "_情報源信頼度", "_state_marker": "_状態印",
        "_source_marker": "_情報源印", "_relation_condition": "_関係条件",
        "_relation_polarity": "_関係極性", "_relation_qualifiers": "_関係修飾",
    },
    "src/minidora/HDS直接関係検証.py": {
        "_relation_name": "_関係名", "_source_id": "_情報源ID", "_candidate_edges": "_候補辺",
    },
    "src/minidora/HDS関係図推論.py": {"_relation": "_関係"},
    "src/minidora/hds作業状態.py": {"_source_id": "_情報源ID", "_support_state": "_支持状態"},
    "src/minidora/hds統一状態循環.py": {"_checkpoint": "_検査点"},
    "src/minidora/K3評価.py": {"run_k3_equivalence_benchmark": "K3同等性評価を実行"},
    "src/minidora/K3機能.py": {"Candidate": "候補"},
    "src/minidora/K3生成.py": {"context_features": "文脈特徴"},
    "src/minidora/K3_HDSネイティブ.py": {
        "_relation_name_from_predicate": "_述語から関係名",
        "_source_group_id": "_情報源群ID",
        "_fact_source_map": "_事実情報源対応",
        "_relation_similarity": "_関係類似度",
    },
    "src/minidora/会話作用契約.py": {"source": "情報源"},
    "src/minidora/多段解決.py": {"capability": "能力", "reference": "参照"},
    "src/minidora/模型.py": {"checkpoint": "検査点"},
    "src/minidora/科学専門能力_共通.py": {
        "_choice_numeric": "_選択肢数値", "_choice_contains": "_選択肢包含",
        "_result": "_結果", "_generic_result": "_一般結果",
    },
    "src/minidora/科学専門能力_構造.py": {
        "_choice_scalar": "_選択肢スカラー", "_parse_state": "_状態解析",
        "_projection_probability": "_射影確率",
    },
    "src/minidora/製品版/製品チャット.py": {"_core": "_模型核"},
    "src/minidora/言語基底_英日意味強化.py": {
        "_generic_relation_question": "_一般関係質問", "_fallback_question": "_代替質問",
    },
    "src/minidora/言語確率法則.py": {
        "_確率_for_context": "_文脈確率", "_分布_for_context": "_文脈分布",
    },
    "tests/test_HDS並列構文化.py": {"_candidate": "_候補", "_Compiler": "_構文化器"},
    "tests/test_HDS作業状態.py": {"_weak_relation": "_弱関係", "_core": "_模型核"},
    "tests/test_HDS再生.py": {"_choice_row": "_選択肢行"},
    "tests/test_HDS再生比較.py": {"_result": "_結果"},
    "tests/test_HDS再生記録.py": {"_Compiler": "_構文化器"},
    "tests/test_HDS再生評価.py": {"_candidate": "_候補"},
    "tests/test_HDS判断主体.py": {"model_result": "模型結果"},
    "tests/test_HDS参照.py": {"_Compiler": "_構文化器"},
    "tests/test_HDS監督選択実行系.py": {"result": "結果"},
    "tests/test_HDS直接関係検証.py": {"_assertion_candidate": "_主張候補"},
    "tests/test_HDS統合判断主体_v1.py": {"choice_ir": "選択中間表現"},
    "tests/test_HDS能力経路_v2.py": {"_query_choice": "_問合せ選択肢"},
    "tests/test_HDS適応候補調停.py": {"_result": "_結果"},
    "tests/test_HDS選択仮説.py": {"_candidate": "_候補"},
    "tests/test_HDS関係図推論.py": {"_relation_ir": "_関係中間表現"},
    "tests/test_K3例外除去.py": {"_candidate": "_候補"},
    "tests/test_K3有向関係.py": {"_direction_candidate": "_方向候補"},
    "tests/test_命題会話.py": {"Core": "模型核"},
    "tests/test_命題推論.py": {"result": "結果"},
    "tests/test_多段解決.py": {"action": "作用"},
    "tests/test_多段解決_合成.py": {"source": "情報源"},
    "tests/test_実行系_HDS_v1.py": {"_candidate": "_候補", "Compiler": "構文化器"},
    "tests/test_実行系_HDS作業再照合.py": {"_candidate": "_候補", "_Compiler": "_構文化器"},
    "tests/test_実行系_HDS選択.py": {"_candidate": "_候補", "_Compiler": "_構文化器"},
    "tests/test_実行系射影_v15.py": {"_synthetic_relation_ir": "_合成関係中間表現"},
    "tests/test_応答構成_合成.py": {"pipeline": "処理系列"},
    "tests/test_改善統合境界.py": {"gate": "関門"},
    "tests/test_文脈場合分け.py": {"result": "結果"},
    "tests/test_文脈帰属.py": {"result": "結果"},
    "tests/test_最小汎用模型核改善_round2.py": {"Compiler": "構文化器"},
    "tests/test_構成再現_v3.py": {"relation": "関係"},
    "tests/test_模型核回復方針_v1.py": {"_registry": "_登録簿"},
    "tests/test_模型核局所観測単調性_v1.py": {"_result": "_結果"},
    "tests/test_監査改善.py": {"result": "結果"},
    "tests/test_知識取得.py": {"candidate": "候補"},
    "tests/test_科学専門能力_構造.py": {"assert_solver": "解決器を確認"},
    "tests/test_科学専門能力_追加.py": {"assert_solver": "解決器を確認"},
    "tests/test_第24意味と計測.py": {"context": "文脈"},
    "tests/test_証拠統合.py": {"source": "情報源"},
    "tests/test_証拠統合_合成.py": {"pipeline": "処理系列"},
    "tests/test_長文脈_合成.py": {"context": "文脈"},
    "tests/test_開放関係実行系_v16.py": {"_relation": "_関係", "_Compiler": "_構文化器"},
    "tools/K3公開成果物目録.py": {"_manifest_bytes": "_目録バイト列"},
    "tools/模型核24修復_AB.py": {"_reference_dict": "_参照辞書", "_result_dict": "_結果辞書"},
    "tools/HDS再生除去比較.py": {"_summary": "_要約"},
    "tools/射影連鎖監査.py": {
        "_relation_is_question": "_関係は質問か", "_semantic_bridge_question": "_意味接続質問",
        "_semantic_loss": "_意味損失", "_relation_types": "_関係種別群",
    },
    "tools/形式評価.py": {"_監督_result_payload": "_監督結果構造"},
    "tools/形式評価_科学能力_AB.py": {"_科学専門能力_result_payload": "_科学専門能力結果構造"},
    "tools/製品能力モジュール実証.py": {"core": "模型核", "Fallback": "代替経路"},
    "tools/評価.py": {"_result_payload": "_結果構造"},
}

試験識別子置換 = {
    "test_plan_is_separate_from_archive_and_has_lease": "test_計画は正本保管と分離され有効期限を持つ",
    "test_candidate_change_rebinds_plan": "test_候補変化で計画を再束縛する",
    "test_subject_change_is_a_real_plan_invalidation_condition": "test_主体変化は計画失効条件になる",
    "test_parallel_pass_disagreement_opens_global_reconcile": "test_並列通過の不一致で大域再照合を開く",
    "test_formation_is_not_active_until_explicitly_approved": "test_形成は明示承認まで有効化しない",
    "test_effect_audit_requires_downstream_difference": "test_作用実効監査は後続差を要求する",
    "test_web_search_route_and_references": "test_Web検索経路と参照",
    "test_query_cleanup": "test_検索語整形",
    "test_search_then_summary_uses_search_references": "test_検索後要約は検索参照を使う",
    "test_searxng_json_mapping": "test_SearXNG_JSON対応",
    "test_search_failure_holds_without_core": "test_検索失敗時は模型核なしで保留",
    "test_existing_approve_is_exactly_transparent": "test_既存承認は完全透過する",
    "test_suspend_can_only_add_new_closure": "test_保留は新規閉包だけを追加する",
    "test_runtime_transitive_import_graph_excludes_experimental_unified_path": "test_実行系推移依存から実験統一経路を除外する",
    "test_runtime_choice_path_is_formal_core_plus_hds_supervisory_intervention": "test_実行系選択経路は形式模型核とHDS監督介入である",
    "test_news_then_summary": "test_ニュース後要約",
    "test_explicit_summary": "test_明示要約",
    "test_bullet_transform": "test_箇条書き変換",
    "test_extract_numbers": "test_数値抽出",
    "test_calculation": "test_計算",
    "test_core_fallback": "test_模型核代替経路",
    "test_basic_chat": "test_基本会話",
    "test_trace_contains_route_selection": "test_追跡記録に経路選択を含む",
    "test_knowledge_reference": "test_知識参照",
    "test_news_summary_uses_reference_body": "test_ニュース要約は参照本文を使う",
    "test_session_isolation": "test_会話単位を分離する",
    "test_dynamic_module_registration": "test_動的能力モジュール登録",
    "test_health": "test_正常性",
    "test_static_ui": "test_静的画面",
    "test_chat_and_trace": "test_会話と追跡記録",
    "test_validation": "test_入力検証",
    "test_live_gpqa_is_canonical_and_fixed_reference_is_forbidden": "test_実参照GPQAが正本で固定参照は禁止",
    "test_canonical_protocol_accepts_minidora30_conditions": "test_正本手順はMINIDORA30条件を受理する",
    "test_partial_gpqa_is_rejected_as_canonical": "test_GPQA部分実行は正本として拒否する",
    "test_openalex_condition_change_is_rejected": "test_OpenAlex条件変更を拒否する",
    "test_dataset_hash_change_is_rejected": "test_資料集合ハッシュ変更を拒否する",
    "test_live_gpqa_is_not_cross_run_code_only_delta": "test_実参照GPQAは実行間コード差のみではない",
    "test_required_benchmark_contract_assets_exist": "test_必須評価契約資産が存在する",
    "test_canonical_separates_minidora30_core_and_minidora80_system_live_only": "test_正本はMINIDORA30模型核とMINIDORA80システムを分離する",
    "test_agents_enforces_gpqa_no_fixed_reference_policy": "test_AGENTSはGPQA固定参照禁止を要求する",
    "test_strict_runner_has_no_gpqa_fixed_replay_entry": "test_厳密評価入口にGPQA固定再生経路がない",
    "test_tools_readme_declares_live_only_canonical_runner": "test_ツール説明は実参照正本評価入口を宣言する",
    "test_minidora30_manifest_is_machine_locked": "test_MINIDORA30目録は機械固定される",
    "test_minidora80_manifest_is_machine_locked": "test_MINIDORA80目録は機械固定される",
    "test_gpqa_fixed_replay_execution_paths_are_retired": "test_GPQA固定再生実行経路は廃止済み",
}

説明語置換 = {
    "Core": "模型核", "core": "模型核", "Module": "能力モジュール", "Capability": "能力",
    "Compiler": "構文化器", "Architecture": "構造", "Pipeline": "処理系列", "Runtime": "実行系",
    "Gate": "関門", "scope": "範囲", "solver": "解決器", "helper": "補助器",
    "benchmark": "外部評価", "fallback": "代替経路", "registry": "登録簿",
    "checkpoint": "検査点", "manifest": "目録", "inventory": "目録",
    "winner selection": "最有力候補選択", "Replay": "再生", "baseline": "対照基準",
    "Data": "資料", "Knowledge": "知識", "Compute": "計算",
}


def _互換モジュール本文(正本: str) -> str:
    モジュール = Path(正本).stem
    return (
        f'"""旧英字名の互換入口。現行正本は `{Path(正本).name}`。"""\n'
        'from importlib import import_module as _読込\n'
        f'_正本 = _読込(".{モジュール}", __package__)\n'
        'for _名, _値 in vars(_正本).items():\n'
        '    if _名 not in {"__name__", "__package__", "__loader__", "__spec__", "__file__", "__cached__"}:\n'
        '        globals()[_名] = _値\n'
    )


def _互換ツール本文(正本: str) -> str:
    名 = Path(正本).name
    return (
        f'"""旧英字名の互換入口。現行正本は `{名}`。"""\n'
        'from pathlib import Path\n'
        'import runpy\n\n'
        f'_正本経路 = Path(__file__).with_name("{名}")\n'
        '_名前空間 = runpy.run_path(str(_正本経路), run_name="_minidora_互換")\n'
        'for _名, _値 in _名前空間.items():\n'
        '    if not _名.startswith("__"):\n'
        '        globals()[_名] = _値\n'
        'if __name__ == "__main__" and callable(_名前空間.get("main")):\n'
        '    raise SystemExit(_名前空間["main"]())\n'
    )


def _移動と互換入口(対応: dict[str, str], ツール: bool = False) -> None:
    for 旧相対, 新相対 in 対応.items():
        旧 = 根 / 旧相対
        新 = 根 / 新相対
        if not 旧.exists():
            continue
        if not 新.exists():
            新.parent.mkdir(parents=True, exist_ok=True)
            新.write_text(旧.read_text(encoding="utf-8"), encoding="utf-8")
        旧.write_text(_互換ツール本文(新相対) if ツール else _互換モジュール本文(新相対), encoding="utf-8")


def _試験移動() -> None:
    for 旧相対, 新相対 in 試験移動.items():
        旧 = 根 / 旧相対
        新 = 根 / 新相対
        if 旧.exists() and not 新.exists():
            旧.rename(新)


def _既存互換入口明示() -> None:
    for 相対 in 既存互換入口:
        対象 = 根 / 相対
        if not 対象.exists():
            continue
        本文 = 対象.read_text(encoding="utf-8")
        if "互換入口" not in 本文[:800]:
            対象.write_text(f'"""旧英字名の互換入口。日本語正本へ委譲する。"""\n' + 本文, encoding="utf-8")


def _設計互換案内明示() -> None:
    for 相対, 正本名 in 設計互換案内.items():
        対象 = 根 / 相対
        if 対象.exists():
            対象.write_text(
                f"# 旧英字名の互換案内\n\n現行日本語正本は [`{正本名}`]({正本名})。\n",
                encoding="utf-8",
            )


def _全テキスト置換(対応: dict[str, str]) -> None:
    対象拡張子 = {".py", ".md", ".yml", ".yaml", ".toml", ".json", ".jsonl", ".ps1"}
    除外先頭 = ("docs/", "artifacts/", "構文化/正本パッケージ/")
    for 対象 in 根.rglob("*"):
        if not 対象.is_file() or 対象.suffix.lower() not in 対象拡張子:
            continue
        相対 = 対象.relative_to(根).as_posix()
        if 相対.startswith(除外先頭):
            continue
        try:
            本文 = 対象.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        新本文 = 本文
        for 旧, 新 in 対応.items():
            新本文 = 新本文.replace(旧, 新)
        if 新本文 != 本文:
            対象.write_text(新本文, encoding="utf-8")


def _識別子置換(対象: Path, 対応: dict[str, str]) -> None:
    本文 = 対象.read_text(encoding="utf-8")
    出力 = []
    for 字句 in tokenize.generate_tokens(io.StringIO(本文).readline):
        if 字句.type == tokenize.NAME and 字句.string in 対応:
            字句 = tokenize.TokenInfo(字句.type, 対応[字句.string], 字句.start, 字句.end, 字句.line)
        出力.append(字句)
    新本文 = tokenize.untokenize(出力)
    if 新本文 != 本文:
        対象.write_text(新本文, encoding="utf-8")


def _識別子正規化() -> None:
    for 相対, 対応 in 識別子置換.items():
        対象 = 根 / 相対
        if 対象.exists():
            _識別子置換(対象, 対応)

    for 対象 in (根 / "tests").glob("test_*.py"):
        _識別子置換(対象, 試験識別子置換)


def _状態値正規化() -> None:
    for 基点 in (根 / "src/minidora", 根 / "tests", 根 / "tools"):
        for 対象 in 基点.rglob("*.py"):
            if 対象.name == "日本語基底監査.py":
                continue
            本文 = 対象.read_text(encoding="utf-8")
            新本文 = 本文
            for 旧, 新 in 状態値置換.items():
                新本文 = 新本文.replace(f'"{旧}"', f'"{新}"').replace(f"'{旧}'", f"'{新}'")
            if 新本文 != 本文:
                対象.write_text(新本文, encoding="utf-8")


def _説明語正規化() -> None:
    対象群 = (
        "README.md", "現行正本.md", "参照正本.md", "AGENTS.md",
        "設計/README.md", "src/README.md", "tests/README.md", "tools/README.md",
        "製品版/README.md", "aistudio/README.md",
    )
    for 相対 in 対象群:
        対象 = 根 / 相対
        if not 対象.exists():
            continue
        本文 = 対象.read_text(encoding="utf-8")
        新行群: list[str] = []
        for 行 in 本文.splitlines():
            if any(印 in 行 for 印 in ("http://", "https://", "旧英字", "互換名")):
                新行群.append(行)
                continue
            新行 = 行
            for 旧, 新 in 説明語置換.items():
                新行 = re.sub(rf"(?<![A-Za-z]){re.escape(旧)}(?![A-Za-z])", 新, 新行)
            新行群.append(新行)
        新本文 = "\n".join(新行群) + ("\n" if 本文.endswith("\n") else "")
        if 新本文 != 本文:
            対象.write_text(新本文, encoding="utf-8")


def _正本参照補強() -> None:
    規定情報 = (
        "\n## 言語模型成立規定参照\n\n"
        "- リポジトリ: https://github.com/gatchimuchio/LLM-Constitutive-Specification\n"
        "- 参照コミット: `fcbc2fa4bc89d749942e8ebee2764115488d29c4`\n"
        "- 版: `2026-08-28-成立規定-8`\n"
    )
    for 相対 in ("現行正本.md", "src/README.md"):
        対象 = 根 / 相対
        本文 = 対象.read_text(encoding="utf-8")
        if "fcbc2fa4bc89d749942e8ebee2764115488d29c4" not in 本文:
            対象.write_text(本文.rstrip() + "\n" + 規定情報, encoding="utf-8")

    設計README = 根 / "設計/README.md"
    本文 = 設計README.read_text(encoding="utf-8")
    if "01_日本語正本語彙_v1.md" not in 本文:
        本文 = 本文.replace(
            "局所規定: [`00_日本語基底規定_v1.md`](00_日本語基底規定_v1.md)",
            "局所規定: [`00_日本語基底規定_v1.md`](00_日本語基底規定_v1.md) / [`01_日本語正本語彙_v1.md`](01_日本語正本語彙_v1.md)",
        )
        設計README.write_text(本文, encoding="utf-8")


def _監査器自己除外() -> None:
    対象 = 根 / "tools/日本語基底監査.py"
    本文 = 対象.read_text(encoding="utf-8")
    本文 = 本文.replace(
        '        if 対象.name in _外部固定ファイル:\n            continue\n',
        '        if 対象.name in _外部固定ファイル or 対象.name == "README.md":\n            continue\n',
    )
    本文 = 本文.replace(
        '        for 節 in ast.walk(木):\n            if isinstance(節, ast.Constant) and isinstance(節.value, str) and 節.value in _旧状態値:\n                誤り.append(f"内部状態値が旧英語正本のまま: {相対}:{getattr(節, \'lineno\', \'?\')}:{節.value}")\n',
        '        if 対象.name != "日本語基底監査.py":\n            for 節 in ast.walk(木):\n                if isinstance(節, ast.Constant) and isinstance(節.value, str) and 節.value in _旧状態値:\n                    誤り.append(f"内部状態値が旧英語正本のまま: {相対}:{getattr(節, \'lineno\', \'?\')}:{節.value}")\n',
    )
    対象.write_text(本文, encoding="utf-8")


def main() -> int:
    _移動と互換入口(ソース移動)
    _移動と互換入口(ツール移動, ツール=True)
    _試験移動()
    _既存互換入口明示()
    _設計互換案内明示()

    # 先に参照先を日本語正本へ向ける。互換入口は旧名の利用者だけが通る。
    _全テキスト置換(モジュール名置換)
    _全テキスト置換(ツール名置換)
    _識別子正規化()
    _状態値正規化()
    _説明語正規化()
    _正本参照補強()
    _監査器自己除外()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
