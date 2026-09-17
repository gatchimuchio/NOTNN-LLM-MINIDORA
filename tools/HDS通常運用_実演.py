"""同じHDS通常運用から既存能力を使う人工資料の実演。外部通信は行わない。"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from minidora.HDS運用 import HDS運用セッション


def 実演する():
    s = HDS運用セッション('実演')
    事例 = (
        ('資料「A」を登録:{"売上":100,"費用":60}', '登録しました'),
        ('資料「B」を登録:{"売上":80,"費用":45}', '登録しました'),
        ('資料「A」と資料「B」の売上を円で比較して', '-20円'),
        ('訂正:属性は費用です', '-15円'),
        ('詳しく説明して', '-15円'),
        ('資料「A」を更新:{"売上":100,"費用":50}', '更新しました'),
        ('前回の依頼を再実行して', '-5円'),
        ('「(x+1)**3」をxで微分して、その結果を箇条書きにして', '3*x**2 + 6*x + 3'),
        ('本文資料「文」を登録：太郎は猫です。すべての猫は哺乳類です。詳細は図を参照。', '登録しました'),
        ('資料「文」から「太郎は哺乳類である」の根拠を説明して', '未解釈'),
    )
    記録 = []
    for 依頼, 必須本文 in 事例:
        開始 = perf_counter()
        応答 = s.応答(依頼)
        記録.append({'依頼': 依頼, '秒': perf_counter()-開始,
            '合格': 応答.成立 and 必須本文 in 応答.本文, '応答': 応答.辞書化()})
    # 保存前後で既存の比較・読解成果型と次ターンの照応が維持される。
    s = HDS運用セッション.復元(s.保存())
    応答 = s.応答('短く説明して')
    記録.append({'依頼': '保存復元→短く説明して',
        '合格': 応答.成立 and '未解釈' in 応答.本文, '応答': 応答.辞書化()})
    return {'対象': 'HDS-MINIDORA通常運用 第27バッチ', '資料': '人工資料・外部通信なし',
        '件数': len(記録), '合格数': sum(x['合格'] for x in 記録), '事例': 記録}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--出力')
    a = p.parse_args()
    結果 = 実演する()
    本文 = json.dumps(結果, ensure_ascii=False, indent=2, allow_nan=False)
    if a.出力:
        Path(a.出力).write_text(本文 + '\n', encoding='utf-8')
    print(json.dumps({'件数': 結果['件数'], '合格数': 結果['合格数']}, ensure_ascii=False))
    return 0 if 結果['件数'] == 結果['合格数'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
