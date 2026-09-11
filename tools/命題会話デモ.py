"""命題の導出・確認・訂正・失効を実HDSと標準汎用会話で実行する人工資料デモ。"""
from pathlib import Path
import argparse
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from minidora.汎用会話 import 汎用会話セッション


def 実演():
    session = 汎用会話セッション('命題会話デモ')
    script = (
        ('資料「規則」を登録:すべての猫は哺乳類である。太郎は猫である。', '合格', None),
        ('資料「規則」から「太郎は哺乳類である」は言える？', '合格', '支持'),
        ('根拠を説明して', '合格', '支持'),
        ('主張を「太郎は鳥である」に訂正して', '合格', '未確定'),
        ('資料「規則」を更新:すべての猫は哺乳類である。太郎は猫である。太郎は哺乳類ではない。', '合格', None),
        ('根拠を説明して', '保留', None),
        ('資料「規則」から「太郎は哺乳類である」は言える？。詳しく', '合格', '矛盾'),
        ('資料「規則」を更新:太郎は猫である。太郎は鳥ではない。', '合格', None),
        ('資料「規則」から「すべての猫は鳥ではない」は言える？', '確認待ち', None),
        ('解釈は2です', '合格', '支持'),
        ('資料「規則」から「すべての猫は鳥ではない」は言える？', '確認待ち', None),
        ('解釈は1です', '合格', '未確定'),
    )
    rows = []
    for text, state, expected in script:
        result = session.応答(text)
        decision = None
        if result.結果:
            decision = result.結果.データ['元結果'][0]['データ']['判定結果']['判定']
        if result.状態 != state or decision != expected:
            raise RuntimeError('会話接続が期待と不一致:' + text + ':' + result.理由)
        rows.append({'入力': text, '状態': result.状態, '判定': decision, '本文': result.本文,
                     '意味候補数': len((result.追跡 or {}).get('命題解釈候補', ()))})
    return {'種類': '人工資料による実接続。汎用能力ベンチマークではない。', '会話': rows}


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'): stream.reconfigure(encoding='utf-8', errors='strict')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    result = 実演()
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for row in result['会話']:
            print('利用者：' + row['入力'])
            print('MINIDORA［' + row['状態'] + '］：' + row['本文'] + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
