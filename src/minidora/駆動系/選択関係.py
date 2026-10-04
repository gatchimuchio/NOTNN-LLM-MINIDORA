"""候補順位と、目的関係の証明を分離する通常選択用の関係射影。

受け取るのは既存Compilerが形成した関係だけ。原文の第二解析器や、問題名・
正解ラベル・分野別の解答規則は置かない。証拠と規則は既存の関係核で検証する。
"""
from __future__ import annotations
from dataclasses import dataclass, replace
import json
from .契約 import 関係項,関係節,関係証拠,関係保証,関係要求,関係資源契約
from .取得 import 関係を取得
from .変換 import 関係を変換
from .射影 import 関係結果を射影
from .学習 import 関係学習状態,有効形成を取得,実行経験を形成
from .目的不足 import 不足関係を構成
from ..コア.値 import 署名,文字


def 言語関係を節へ(関係):
    """既存の集合端点を順序非依存の一対象として保持する。類似語を同一化しない。"""
    必須=('種別','始点','終点','肯定','条件','述語')
    if any(not hasattr(関係, 名) for 名 in 必須):raise TypeError('Compiler関係契約が不足')
    def 意味集合(値):
        if not isinstance(値,frozenset) or any(not isinstance(x,str) for x in 値):
            raise TypeError('意味端点は文字列frozenset')
        return json.dumps(sorted(値),ensure_ascii=False,separators=(',',':'))
    種別=文字(関係.種別)
    述語=種別
    if 関係.述語:
        述語+=':'+意味集合(関係.述語)
    return 関係節(述語,(('始点',関係項(意味集合(関係.始点),'意味端点')),
                        ('終点',関係項(意味集合(関係.終点),'意味端点'))),
        関係.肯定,tuple(意味集合(x) for x in 関係.条件),範囲='Compiler意味関係')


@dataclass(frozen=True,slots=True)
class 候補関係判定:
    ラベル:str
    対象:tuple
    証明:tuple
    反証:tuple
    不足:tuple
    状態:str
    使用形成:tuple[str,...]=()


@dataclass(frozen=True,slots=True)
class 選択関係結果:
    目的ID:str
    候補:tuple[候補関係判定,...]
    学習提案:関係学習状態
    照合数:int
    未完了:tuple[str,...]=()
    評価規則:str="全節支持"

    @property
    def 一意成立(self):
        群=tuple(x.ラベル for x in self.候補 if x.状態=='成立')
        return 群[0] if len(群)==1 and not self.未完了 else None


def 選択関係を評価(目的ID,世界ID,候補対象,参照関係,*,変換=(),学習状態=None,
                資源=関係資源契約(),停止要求=None,反転=False):
    """連言の全節と反対極性を別に検査する。資料件数を証明へ変換しない。"""
    文字(目的ID);文字(世界ID)
    if type(反転) is not bool:raise TypeError("選択意図の反転はbool")
    if len({k for k,_ in 候補対象})!=len(候補対象):raise ValueError('候補ID重複')
    学習=学習状態 or 関係学習状態()
    証拠=[];既出=set()
    for 出典,関係群 in 参照関係:
        文字(出典)
        for 関係 in 関係群:
            try:
                節=言語関係を節へ(関係)
            except (TypeError, ValueError):
                # 旧模型・試験適合器など型付き関係を供給できない資料は、
                # 関係証明へ昇格させず既存能力側へ残す。
                continue
            鍵=署名((出典,節))
            if 鍵 not in 既出:
                既出.add(鍵);証拠.append(関係証拠('観測:'+鍵,節,(出典,),関係保証.観測))
    行=[];累積=0;未完=[]
    for ラベル,対象群 in 候補対象:
        try:
            対象=tuple(言語関係を節へ(x) for x in 対象群)
        except (TypeError, ValueError):
            対象=()
        if not 対象:
            行.append(候補関係判定(ラベル,(),(),(),(),'対象未構成'));continue
        正,反,不足=[],[],[];使用=set();競合=False
        候補学習=学習
        for 番号,節 in enumerate(対象):
            for 反対検査 in (False,True):
                残り=資源.最大照合-累積
                if 残り<1:
                    未完.append('選択関係の全候補共有予算');break
                問い=replace(節,肯定=not 節.肯定) if 反対検査 else 節
                要求=関係要求(目的ID+':'+ラベル+':'+str(番号)+':'+str(反対検査),
                    '候補を成立させる関係の確認',世界ID,問い,tuple(証拠),tuple(変換),
                    資源=replace(資源,最大照合=残り))
                追加=有効形成を取得(候補学習,要求.変換)
                取得=関係を取得(要求,追加)
                変換結果=関係を変換(要求,取得,停止要求=停止要求)
                出力=関係結果を射影(要求,変換結果,追加)
                累積+=出力.照合数
                if 出力.状態 in ('予算枯渇','停止'):
                    未完.extend(出力.未充足);break
                if 出力.状態=='競合':
                    競合=True;反.append(出力)
                elif 出力.状態=='成立':
                    (反 if 反対検査 else 正).append(出力)
                    使用.update(出力.使用形成)
                    if 反対検査 == 反転:
                        候補学習=実行経験を形成(候補学習,要求,変換結果,出力)
                elif 反対検査 == 反転:
                    残り=資源.最大照合-累積
                    if 残り<=0:未完.append('不足関係の共有予算');break
                    計画要求=replace(要求,資源=replace(資源,最大照合=残り))
                    計画=不足関係を構成(計画要求,追加,利用先=('候補:'+ラベル,),停止要求=停止要求)
                    累積+=計画.照合数
                    不足.extend(計画.不足)
                    if not 計画.完了:未完.extend(計画.理由 or ('不足計画未完了',))
            if 未完:break
        if 競合: 状態='競合'
        elif 未完: 状態='未観測'
        elif 反転: 状態='成立' if 反 else '反証' if len(正)==len(対象) else '未観測'
        else: 状態='反証' if 反 else '成立' if len(正)==len(対象) else '未観測'
        行.append(候補関係判定(ラベル,対象,tuple(正),tuple(反),tuple(不足),状態,tuple(sorted(使用))))
        # 証明のない候補・反証のある候補から、成功形成を採用しない。
        if 状態=='成立':学習=候補学習
    return 選択関係結果(目的ID,tuple(行),学習,累積,tuple(dict.fromkeys(未完)),"連言の明示反証" if 反転 else "全節支持")