from pathlib import Path

p = Path('src/minidora/模型.py')
s = p.read_text(encoding='utf-8')
old = '''        union=frozenset.union(*sigs.values())
        anchors=(_順序識別特徴(文脈.現在.意味語集合,文脈.現在.意味語列)-union)|common
        if not anchors:
            anchors=文脈.現在.意味語集合
'''
new = '''        union=frozenset.union(*sigs.values())
        question_features=_順序識別特徴(文脈.現在.意味語集合,文脈.現在.意味語列)
        # 問い自身に意味anchorが無い場合、候補共通語を問い由来anchorへ偽装しない。
        anchors=((question_features-union)|common) if question_features else frozenset()
        if not anchors and question_features:
            anchors=文脈.現在.意味語集合
'''
if old not in s: raise SystemExit('anchor block drifted')
s = s.replace(old, new, 1)
old = '''                anchor=mass(anchors&tokens)/anchor_mass if anchor_mass else 0.0
                if anchor<=0:
                    continue
'''
new = '''                # 問い側に意味anchorが無い制御的入力では、候補差とDataの局所対応だけを使う。
                # これはData内容の差を保持するための縮退であり、候補IDや正解情報は使わない。
                anchor=mass(anchors&tokens)/anchor_mass if anchor_mass else 1.0
                if anchor<=0:
                    continue
'''
if old not in s: raise SystemExit('anchor fallback block drifted')
s = s.replace(old, new, 1)
old = '''            shared=min(local.values())
            for cid,value in local.items():
                delta=value-shared
                if delta>0:
                    # 多数の弱い資料が、強い局所支持を票数で押し流すのを防ぐ。
                    if delta>score[cid]:
                        score[cid]=delta
                        evidence[cid]=[f"最大局所対応:{ref.識別子 or 'anonymous'}:{delta:.9f}"]
                    elif delta==score[cid]:
                        evidence[cid].append(f"最大局所対応:{ref.識別子 or 'anonymous'}:{delta:.9f}")
'''
new = '''            if anchor_mass <= 0:
                # 問いanchor無しの縮退では、各Data内で候補が一意に識別できた時だけ1観測とする。
                # 同一Dataは文脈化時に重複除去されるため、異なるDataだけが別観測として残る。
                maximum=max(local.values(),default=0.0)
                top=[cid for cid,value in local.items() if value==maximum and value>0]
                if maximum>0 and len(top)==1:
                    cid=top[0]
                    score[cid]+=1.0
                    evidence[cid].append(f"局所対応:{ref.識別子 or 'anonymous'}:1")
                continue
            shared=min(local.values())
            for cid,value in local.items():
                delta=value-shared
                if delta>0:
                    # 意味anchor有りでは、多数の弱い資料が強い局所支持を票数で押し流すのを防ぐ。
                    if delta>score[cid]:
                        score[cid]=delta
                        evidence[cid]=[f"最大局所対応:{ref.識別子 or 'anonymous'}:{delta:.9f}"]
                    elif delta==score[cid]:
                        evidence[cid].append(f"最大局所対応:{ref.識別子 or 'anonymous'}:{delta:.9f}")
'''
if old not in s: raise SystemExit('local scoring block drifted')
p.write_text(s.replace(old,new,1),encoding='utf-8')

p = Path('src/minidora/能力状態差循環.py')
s = p.read_text(encoding='utf-8')
old = '''                # 参照比較だけは元の全候補を維持し、候補除外による人工的な固有語を作らない。
                scope = tuple(internal) if isinstance(action, 候補共同参照作用) else active_rows
'''
new = '''                # 意味anchorを持つ通常問題では元の全候補を維持し、候補除外による人工差を作らない。
                # 意味anchorを持たない制御的入力だけは、既存の状態差循環契約どおりactive境界を再照合する。
                scope = (
                    tuple(internal)
                    if isinstance(action, 候補共同参照作用) and 文脈.現在.意味語集合
                    else active_rows
                )
'''
if old not in s: raise SystemExit('reconcile scope block drifted')
p.write_text(s.replace(old,new,1),encoding='utf-8')
