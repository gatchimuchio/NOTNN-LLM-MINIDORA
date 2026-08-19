#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
from collections import Counter
from pathlib import Path

src = Path('解析/K3全公開データコンパイル/v6/header-probe/header-probe-summary.json')
out = Path('解析/K3全公開データコンパイル/v6/header-probe/HDS適合不能シグネチャ.json')
d = json.loads(src.read_text(encoding='utf-8'))
names = d.get('HDS適合不能tensor名', [])
last1 = Counter()
last2 = Counter()
last3 = Counter()
for n in names:
    p = n.split('.')
    last1['.'.join(p[-1:])] += 1
    last2['.'.join(p[-2:])] += 1
    last3['.'.join(p[-3:])] += 1
report = {
    'count': len(names),
    'last1': dict(last1.most_common()),
    'last2': dict(last2.most_common()),
    'last3': dict(last3.most_common()),
}
out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(report, ensure_ascii=False, indent=2))
