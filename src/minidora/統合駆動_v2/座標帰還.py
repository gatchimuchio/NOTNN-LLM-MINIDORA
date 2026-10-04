"""実ノードの変化と目的条件を、原指示を変えず操作座標へ帰還する。"""
from __future__ import annotations
from dataclasses import replace
from ..コア.指示関係 import 座標状態
from .目的保持 import 目的ノード署名,目的ノード有効
from .指示接続 import 指示を観測


def 進展の利用先(状態,ノード群,作用群):
    """型付き作用契約の生産消費を辿る。ラベル一致だけを寄与証明としない。"""
    指示=状態.指示関係
    if 指示 is None:return ()
    消費索引={}
    for 作用 in 作用群:
        仕様=getattr(作用,'計画仕様',None)
        if 仕様 is None:continue
        for ノード in 仕様.入力ノード集合:
            消費索引.setdefault(ノード,[]).append((仕様.作用ID,仕様.出力ノード集合))
    行=[]
    for 起点 in sorted(ノード群):
        if 起点 == "目的:閉包":
            from ..コア.値 import 署名
            行.append((起点,tuple(x.ID for x in 指示.条件),(),署名((指示.署名,状態.閉包済み))))
            continue
        到達={起点};待ち=[起点];消費者=set()
        while 待ち:
            for 消費者ID,生成群 in 消費索引.get(待ち.pop(),()):
                消費者.add(消費者ID)
                for 次 in 生成群:
                    if 次 not in 到達:到達.add(次);待ち.append(次)
        条件=tuple(x.ID for x in 指示.条件 if x.ノード in 到達 or '指示条件:'+x.ID in 到達)
        # これは寄与経路の契約であり、まだ実行していない消費者を実行済みにしない。
        行.append((起点,条件,tuple(sorted(消費者)),目的ノード署名(状態,起点)))
    return tuple(行)


def 結果を座標へ帰還(前,後,差,作用ID):
    場=後.操作座標
    if 場 is None:return 後
    必要={x.ノード for x in 後.指示関係.条件} | {x.ノード for x in 後.指示関係.帰還先}
    # 影響ノードの参照を保存する。原資料は状態・記憶にあり、署名だけで代替しない。
    変化=tuple((n,目的ノード有効(後,n),目的ノード署名(後,n)) for n in sorted(差.影響対象)
        if n in 必要 or n.startswith(('成果:','認識:','資料:')))
    if not 変化:return 後
    現条件=指示を観測(後)
    記録=(('対象/現在状態/取得',変化),
          ('目的/評価規則/射影',tuple((x.ID,x.判定,x.観測署名) for x in 現条件.条件)),
          ('手段/検証・帰還/射影',(作用ID,前.版,後.版,tuple(n for n,_,_ in 変化))))
    for ID,内容 in 記録:
        面=next(x for x in 場.面 if x.ID==ID)
        if 面.内容==内容:continue
        場=場.帰還(ID,内容,状態=座標状態.確定値,
            根拠=('実行:'+作用ID,'実状態版:'+str(後.版)),理由='実結果と目的条件の照合',期待版=面.版)
    # 確定しているのは「この結果を観測した」という記録。目的が達成したとの宣言ではない。
    return replace(後,操作座標=場)