from pathlib import Path
import sys
sys.path.insert(0,'/mnt/data/minidora_runtime_probe')
sys.path.insert(0,'/mnt/data/HDS_MINIDORA_接続器_v0_1')
from 接続器 import 意味適合参照供給器
from minidora import ミニドラ,要求,手順
R='/mnt/data/K3_MINIDORA_再実行/q19_regression/HDS出力/変換/ミニドラR.jsonl'
p=意味適合参照供給器.JSONL読込(R,最低得点=3.0,最低被覆=0.12)
q='For Equinix, xScale capital expenditure guidance full year 2024 lower upper bounds'
h=p.検索(q,8)
assert h and any('xScale-related on-balance sheet' in x.内容 for x in h)
assert p.検索('banana satellite zoology',8)==()
# 無関係参照はruntimeへ渡らず、参照必須なら保留になる。
r=ミニドラ(p).実行(要求('banana satellite zoology',手順('なし',()),参照必須=True))
assert r.値 is None and not r.参照 and str(r.採否.状態)=='保留'
print('PASS',len(h),r.採否.状態)
