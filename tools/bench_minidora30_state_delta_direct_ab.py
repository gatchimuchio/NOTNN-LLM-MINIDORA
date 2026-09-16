from __future__ import annotations

import argparse
import json
from pathlib import Path

import benchmark as bench
import gpqa_measure_current as gpqa

from minidora.hds_choice_runtime import HDS選択推論実行
from minidora.能力状態差循環 import 標準能力模型核 as 更新模型核
from minidora.能力状態差循環_MINIDORA30 import 標準能力模型核 as MINIDORA30模型核


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    p.add_argument('--start-index', type=int, required=True)
    p.add_argument('--limit', type=int, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--cache-dir', type=Path, default=Path('.cache/minidora-bench'))
    return p


def _row(result, gold: str) -> dict:
    pred = result.回答ラベル
    answered = result.状態 == 'APPROVE' and pred is not None
    return {
        'predicted': pred,
        'answered': answered,
        'correct': bool(answered and pred == gold),
        'status': result.状態,
        'reasons': list(result.理由),
        'checkpoint_reactivations': result.checkpoint再活性数,
        'candidate_cross_updates': result.候補横断更新数,
        'global_reconciliations': result.大域再照合数,
    }


def main() -> int:
    args = _parser().parse_args()
    csv_path, zip_hash, csv_hash = bench._prepare_gpqa_dataset(args.cache_dir, refresh=False)
    cases = gpqa._load_cases(csv_path)
    selected = bench._selected_range(len(cases), args.start_index, args.limit)

    provider = gpqa.一般知識参照供給器(
        OpenAlex_API_key=None,
        Wikipedia言語=('en',),
        timeout=8.0,
        最大本文文字数=6000,
        並列=True,
        最大並列=4,
    )
    ir_compiler = gpqa.汎用意味射影Compiler()
    old_compiler = gpqa.汎用意味射影Compiler()
    new_compiler = gpqa.汎用意味射影Compiler()

    details=[]
    for index in selected:
        question, choices, gold = cases[index]
        question_ir = ir_compiler.問題IR(question, choices)
        references = tuple(gpqa.HDS参照検索(provider, question_ir))

        def run_old():
            return HDS選択推論実行(
                question_ir,
                references,
                コンパイル=old_compiler.コンパイル,
                基礎能力核=None,
                模型核=MINIDORA30模型核(),
                正式模型評価=True,
            )

        def run_new():
            return HDS選択推論実行(
                question_ir,
                references,
                コンパイル=new_compiler.コンパイル,
                基礎能力核=None,
                模型核=更新模型核(),
                正式模型評価=True,
            )

        # 順序依存監査のため偶奇で実行順を反転する。各系は独立Compiler・独立模型核を使用。
        if index % 2 == 0:
            old_result = run_old(); new_result = run_new()
        else:
            new_result = run_new(); old_result = run_old()

        old = _row(old_result, gold)
        new = _row(new_result, gold)
        details.append({
            'index': index,
            'gold': gold,
            'retrieved': len(references),
            'reference_ids': [r.識別子 for r in references],
            'old': old,
            'new': new,
        })
        print(
            f"CASE {index+1:03d}/198 old={old['predicted']} new={new['predicted']} "
            f"old_ok={old['correct']} new_ok={new['correct']} R={len(references)}",
            flush=True,
        )

    old_correct=sum(bool(x['old']['correct']) for x in details)
    new_correct=sum(bool(x['new']['correct']) for x in details)
    old_answered=sum(bool(x['old']['answered']) for x in details)
    new_answered=sum(bool(x['new']['answered']) for x in details)
    changed=sum(x['old']['predicted'] != x['new']['predicted'] for x in details)
    improved=sum(x['new']['correct'] and not x['old']['correct'] for x in details)
    regressed=sum(x['old']['correct'] and not x['new']['correct'] for x in details)
    payload={
        'schema':'minidora.gpqa.state-delta-direct-ab.v1',
        'protocol':{
            'dataset_zip_sha256':zip_hash,
            'dataset_csv_sha256':csv_hash,
            'seed':0,
            'openalex':False,
            'wikipedia_languages':['en'],
            'selected':list(selected),
            'same_question_ir':True,
            'same_reference_records':True,
            'same_reference_identity':True,
            'gold_after_both_inferences':True,
            'old_core':'MINIDORA30 src/minidora/能力状態差循環.py @ a3473fbd',
            'new_core':'same MINIDORA30 + src/minidora/能力状態差循環.py @ 9e797fc only',
            'supervisory_additional_reference':False,
        },
        'metrics':{
            'old_correct':old_correct,
            'new_correct':new_correct,
            'correct_delta':new_correct-old_correct,
            'old_answered':old_answered,
            'new_answered':new_answered,
            'answered_delta':new_answered-old_answered,
            'changed_answers':changed,
            'improved_cases':improved,
            'regressed_cases':regressed,
            'net_improved_cases':improved-regressed,
        },
        'details':details,
    }
    args.out.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(payload['metrics'],ensure_ascii=False),flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
