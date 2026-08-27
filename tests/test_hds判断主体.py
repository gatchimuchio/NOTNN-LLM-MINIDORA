from __future__ import annotations

from minidora.hds_ir import HDSIR,HDS座標,HDS関係,HDS残差,HDS実行核,値状態
from minidora.hds_model_projection import HDSMINIDORA模型評価


def ir(text, coords=(), rels=(), residuals=(), *, kind='knowledge_query'):
    return HDSIR(原文=text,正規化文=text,認知世界ID='hds-j-test',座標=tuple(coords),関係=tuple(rels),残差=tuple(residuals),意味作用履歴=(),実行核=HDS実行核(),入力言語='en',種別=kind)

def candidate(name, pred='stabilize', positive=True):
    return ir(name,(
        HDS座標('s','対象.始点','enzyme'),HDS座標('o','対象.終点',name),
    ),(HDS関係('r',('s',),('o',),'作用',(f'検索述語={pred}', '極性=否定') if not positive else (f'検索述語={pred}',)),))

def evidence(name, pred='stabilize', positive=True):
    return candidate(name,pred,positive)

def question(*, reverse=False, residual=False):
    cond=['検索述語=stabilize','不足位置=終点']
    if reverse: cond.append('選択意図=反転')
    return ir('Which option?',(
        HDS座標('s','対象.始点','enzyme'),HDS座標('u','目的.未知終点','option',値状態.未観測),
    ),(HDS関係('q',('s',),('u',),'問い適合',tuple(cond),値状態.未観測),),
      (HDS残差('loss','semantic_loss','?','unresolved'),) if residual else ())


def test_hds_j_is_final_authority_and_selects_unique_exact_evidence():
    q=question(); c={'A':candidate('alpha'),'B':candidate('beta')}
    result=HDSMINIDORA模型評価(q,c,(evidence('beta'),),参照識別子=('source-b',),参照信頼=(1.0,))
    assert result.状態=='APPROVE'
    assert result.回答ラベル=='B'
    assert result.HDS判断 is not None
    assert result.HDS判断.運用状態=='COMMIT'
    assert 'HDS_JUDGEMENT_SELECTED' in result.理由


def test_shared_source_that_supports_two_candidates_does_not_commit():
    q=question(); c={'A':candidate('alpha'),'B':candidate('beta')}
    data=ir('both',(
        HDS座標('s','対象.始点','enzyme'),HDS座標('a','対象.終点','alpha'),HDS座標('b','対象.終点','beta'),
    ),(
        HDS関係('ra',('s',),('a',),'作用',('検索述語=stabilize',)),
        HDS関係('rb',('s',),('b',),'作用',('検索述語=stabilize',)),
    ))
    result=HDSMINIDORA模型評価(q,c,(data,),参照識別子=('shared',))
    assert result.状態=='SUSPEND'
    assert result.回答ラベル is None


def test_competing_independent_exact_sources_are_held_not_ranked():
    q=question(); c={'A':candidate('alpha'),'B':candidate('beta')}
    result=HDSMINIDORA模型評価(q,c,(evidence('alpha'),evidence('beta')),参照識別子=('sa','sb'))
    assert result.状態=='SUSPEND'
    assert 'HDS_COMPETING_EVIDENCE' in result.理由


def test_exact_positive_and_exact_negative_is_unresolved_contradiction():
    q=question(); c={'A':candidate('alpha'),'B':candidate('beta')}
    result=HDSMINIDORA模型評価(q,c,(evidence('alpha'),evidence('alpha',positive=False)),参照識別子=('pos','neg'))
    assert result.状態=='SUSPEND'
    assert 'HDS_UNRESOLVED_CONTRADICTION' in result.理由


def test_weak_scope_only_support_is_retained_but_not_committed():
    q=question(); c={'A':candidate('alpha'),'B':candidate('beta')}
    weak=ir('weak',(
        HDS座標('s','対象.始点','enzyme'),HDS座標('o','対象.終点','alpha'),
    ),(HDS関係('r',('s',),('o',),'作用',('検索述語=stabilize','条件scope=special')),))
    result=HDSMINIDORA模型評価(q,c,(weak,),参照識別子=('weak-source',))
    assert result.状態=='SUSPEND'
    assert result.HDS判断.候補状態[0].状態 in {'WEAK_EVIDENCE','UNSUPPORTED'}


def test_exception_is_n_minus_one_elimination_not_lowest_score_vote():
    q=question(reverse=True)
    c={'A':candidate('alpha'),'B':candidate('beta'),'C':candidate('gamma')}
    result=HDSMINIDORA模型評価(q,c,(evidence('alpha'),evidence('beta')),参照識別子=('sa','sb'))
    assert result.状態=='APPROVE'
    assert result.回答ラベル=='C'
    assert 'HDS_EXCEPTION_N_MINUS_ONE' in result.理由


def test_semantic_loss_stays_suspended_before_commit():
    q=question(residual=True); c={'A':candidate('alpha'),'B':candidate('beta')}
    result=HDSMINIDORA模型評価(q,c,(evidence('alpha'),),参照識別子=('sa',))
    assert result.状態=='SUSPEND'
    assert 'HDS_FRAME_UNCLOSED' in result.理由


def test_source_and_candidate_order_do_not_change_hds_decision():
    q=question(); a=candidate('alpha'); b=candidate('beta'); ra=evidence('alpha')
    x=HDSMINIDORA模型評価(q,{'A':a,'B':b},(ra,),参照識別子=('sa',))
    y=HDSMINIDORA模型評価(q,{'B':b,'A':a},(ra,),参照識別子=('sa',))
    assert (x.状態,x.回答ラベル,x.HDS判断.候補状態)==(y.状態,y.回答ラベル,y.HDS判断.候補状態)


def test_c_reference_winner_is_proposal_not_authority():
    q=question()
    c={'A':ir('alpha distinctive'),'B':candidate('beta')}
    token_refs=tuple(ir('alpha distinctive') for _ in range(4))
    relation_ref=ir('beta relation',(
        HDS座標('s','対象.始点','enzyme'),HDS座標('o','対象.終点','beta'),
    ),(HDS関係('r',('s',),('o',),'作用',('検索述語=stabilize',)),))
    refs=(*token_refs,relation_ref)
    ids=('ta1','ta2','ta3','ta4','rb')
    result=HDSMINIDORA模型評価(q,c,refs,参照識別子=ids)
    assert result.模型結果.参照最有力候補ID=='A'
    assert result.状態=='APPROVE'
    assert result.回答ラベル=='B'
    assert result.HDS判断.選択候補ID=='B'


def test_no_reference_never_becomes_hds_approval():
    q=question(); c={'A':candidate('alpha'),'B':candidate('beta')}
    result=HDSMINIDORA模型評価(q,c,())
    assert result.状態=='SUSPEND'
    assert result.回答ラベル is None
