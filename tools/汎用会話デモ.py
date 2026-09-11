"""人工資料の比較・確認・訂正・再計画を実HDSと実部品で動かす。Webは呼ばない。"""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from minidora.汎用会話 import 汎用会話セッション
from minidora.製品版.型 import 能力結果


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='strict')
    print('人工資料による動作例。GPT-4との能力比較・公開Web実測ではありません。')
    session = 汎用会話セッション('同一目的での再計画デモ')
    materials = {
        '基準': 能力結果(True, '{"売上":75,"単位":"円"}'),
        '比較先': 能力結果(True, '{"部門":{"売上":60,"単位":"円"}}'),
    }
    cases = [('資料「基準」と資料「比較先」の売上を比較して', materials, '合格'),
             ('それを詳しく説明して', None, '合格')]
    confirmation = 汎用会話セッション('確認と訂正デモ')
    inputs = {'A': 能力結果(True, '{"売上":75,"費用":50}'),
              'B': 能力結果(True, '{"売上":60,"費用":40}')}
    cases2 = [('この2つの売上を比較して', inputs, '確認待ち'),
              ('単位は円です', None, '合格'),
              ('訂正:属性は費用です', None, '合格'),
              ('x**3をxで微分した結果は？', None, '合格'),
              ('それをxで微分して', None, '合格')]
    failed = False
    for s, group in ((session, cases), (confirmation, cases2)):
        for text, data, expected in group:
            result = s.応答(text, data)
            print('\n利用者：' + text)
            print('MINIDORA [' + result.状態 + ']：\n' + result.本文)
            changes = (result.追跡 or {}).get('再計画', [])
            if changes:
                print('失敗からの再計画：' + ' → '.join(x['種別'] for x in changes))
            if result.状態 != expected:
                failed = True
    return 2 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
