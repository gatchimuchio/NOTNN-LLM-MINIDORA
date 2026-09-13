"""JSONLの要求と期待値を分離して評価する。入力者の「独立」宣言を認証しない。"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import platform
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from minidora.監査改善接続 import 改善計画を実行, 改善回答を検査

評価版 = 'MINIDORA-分離入力評価-v0.1'


def _辞書重複禁止(pairs):
    output = {}
    for key,value in pairs:
        if key in output: raise ValueError('JSONの重複キー')
        output[key] = value
    return output


def JSON読取(text):
    def invalid(value): raise ValueError('非有限数は未対応')
    return json.loads(text, object_pairs_hook=_辞書重複禁止, parse_constant=invalid)


def ケースを読む(path: Path):
    if path.stat().st_size > 2_000_000: raise ValueError('評価入力のサイズ上限')
    raw = path.read_bytes()
    rows = []
    ids = set()
    for line in raw.decode('utf-8-sig').splitlines():
        if not line.strip(): continue
        row = JSON読取(line)
        if type(row) is not dict or set(row) != {'ID', '区分', '種類', '要求', '期待'}:
            raise ValueError('ケースの欄不正')
        if type(row['ID']) is not str or not row['ID'] or len(row['ID'])>128 or row['ID'] in ids:
            raise ValueError('ケースID不正又は重複')
        ids.add(row['ID'])
        if row['区分'] not in ('開発生成', '外部提供') or row['種類'] not in ('命題','仮説','介入'):
            raise ValueError('ケース分類不正')
        if type(row['要求']) is not dict or type(row['期待']) is not dict:
            raise ValueError('要求と期待は別の辞書')
        expected = row['期待']
        if not {'状態'} <= set(expected) <= {'状態','判定','仮説集合','介入後'}:
            raise ValueError('期待値の欄不正')
        if expected['状態'] not in ('合格','保留','失敗'):
            raise ValueError('期待する実行状態不正')
        # 成功だけを期待する評価は、意味内容を測ったことにできない。
        required = {'命題':'判定','仮説':'仮説集合','介入':'介入後'}[row['種類']]
        if expected['状態']=='合格' and required not in expected:
            raise ValueError('成功ケースは意味内容の期待値が必要')
        if expected['状態']!='合格' and set(expected)!={'状態'}:
            raise ValueError('未成立ケースに意味内容の期待値を置かない')
        if '判定' in expected and expected['判定'] not in ('支持','反証','矛盾','未確定','解釈依存'):
            raise ValueError('命題の期待判定不正')
        if '仮説集合' in expected and (type(expected['仮説集合']) is not list or
            any(type(x) is not list or any(type(y) is not str for y in x) for x in expected['仮説集合'])):
            raise ValueError('期待仮説集合の型不正')
        if '介入後' in expected and (type(expected['介入後']) is not dict or
            any(type(k) is not str or type(v) is not bool for k,v in expected['介入後'].items())):
            raise ValueError('期待する介入状態の型不正')
        rows.append(row)
        if len(rows)>2000:raise ValueError('評価ケース数上限')
    if not rows: raise ValueError('評価ケースなし')
    return rows, sha256(raw).hexdigest()


def _集合(values):
    return sorted(sorted(set(row)) for row in values)


def 評価する(rows, *, 実行器=改善計画を実行):
    details = []
    for row in rows:
        # 識別子・期待値・由来区分は実行器へ渡さない。
        try:
            out = 実行器(row['種類'], deepcopy(row['要求']), 詳細=False)
            observed = {'状態':out.状態}
            integrity = out.監査整合()
            content = False
            if out.成立:
                answer = out.出力[0][1].データ
                integrity = integrity and 改善回答を検査(answer)
                report = answer['報告']
                if row['種類']=='命題':
                    observed['判定']=report['状態']
                    content = report['状態'] in ('支持','反証','矛盾')
                elif row['種類']=='仮説':
                    observed['仮説集合']=_集合(c['仮説'] for c in report['候補'])
                    # 説明なしや背景不整合を、有効な説明候補獲得と数えない。
                    content = report['状態']=='説明候補あり'
                else:
                    observed['介入後']=report['介入後']
                    content = True
            expected = deepcopy(row['期待'])
            if '仮説集合' in expected: expected['仮説集合']=_集合(expected['仮説集合'])
            correct = integrity and observed==expected
            details.append({'ID':row['ID'],'区分':row['区分'],'種類':row['種類'],
                '期待':expected,'観測':observed,'整合':integrity,'一致':correct,
                '実質回答':bool(out.成立 and content),'例外':None})
        except Exception as exc:
            # 実行器の例外は正常な保留にせず、評価失敗として別計上する。
            details.append({'ID':row['ID'],'区分':row['区分'],'種類':row['種類'],
                '期待':row['期待'],'観測':None,'整合':False,'一致':False,
                '実質回答':False,'例外':type(exc).__name__})

    def 集計(items):
        total = len(items)
        correct = sum(r['一致'] for r in items)
        substantive = [r for r in items if r['実質回答']]
        return {'件数':total,'期待一致':correct,'期待不一致':total-correct,
                '実行例外':sum(r['例外'] is not None for r in items),
                '実質回答数':len(substantive),
                '実質回答率':len(substantive)/total if total else None,
                '実質回答中の期待一致率':sum(r['一致'] for r in substantive)/len(substantive) if substantive else None,
                '正常な保留数':sum(r['観測'] is not None and r['観測']['状態']=='保留' for r in items),
                '意味未確定数':sum(r['観測'] is not None and r['観測'].get('判定') in ('未確定','解釈依存') for r in items)}
    return {'集計':集計(details),'区分別':{k:集計([r for r in details if r['区分']==k])
            for k in ('開発生成','外部提供')},'ケース':details}


def ソース指紋():
    hashes = {str(p.relative_to(ROOT)).replace('\\','/'):sha256(p.read_bytes()).hexdigest()
              for p in sorted((ROOT/'src').rglob('*.py'))}
    encoded=json.dumps(hashes,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
    return {'ファイルSHA256':hashes,'一覧SHA256':sha256(encoded).hexdigest()}


from minidora.標準入出力 import 標準入出力をUTF8にする

def main():
    標準入出力をUTF8にする()
    parser=argparse.ArgumentParser(description='独立したJSONL入力を評価する。外部性・盲検性の認証は行わない。')
    parser.add_argument('--入力',type=Path,required=True)
    parser.add_argument('--出力',type=Path,required=True)
    args=parser.parse_args()
    rows,data_hash=ケースを読む(args.入力)
    report={'版':評価版,'入力SHA256':data_hash,'ソース':ソース指紋(),
        '環境':{'Python':platform.python_version(),'OS':platform.system()},
        '評価UTC':datetime.now(timezone.utc).isoformat(),
        '外部汎化認定':False,
        '限界':'期待一致は開発回帰の指標。外部提供ラベルは申告であり、独立作成・未見性・実世界汎化の証拠ではない。',
        **評価する(rows)}
    args.出力.parent.mkdir(parents=True,exist_ok=True)
    args.出力.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report['集計'],ensure_ascii=False))
    return 0 if report['集計']['期待不一致']==0 else 1

if __name__=='__main__':raise SystemExit(main())
