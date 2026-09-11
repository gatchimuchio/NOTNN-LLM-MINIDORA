"""新しい意味作用を既存合成器へ登録する。取得報告と取得成立を明確に分離する。"""
from __future__ import annotations
from copy import deepcopy
from .能力合成 import 登録能力, _結果辞書
from .応答構成 import 能力結果を復元
from .会話数量 import 会話数量版,表数量を読む,記載数量を読む,数量を比較,会話処理不成立
from .会話回答 import 会話回答版,回答を構成,回答を再表現
from .会話意味 import 意味指紋
from .製品版.型 import 能力結果
from .知識取得接続 import 知識取得Module

会話能力版='MINIDORA-会話能力-v0.2'


def _入力(context):
    aux=context.補助
    if type(aux) is not dict: raise ValueError('合成入力が必要')
    rows=aux.get('合成入力',());settings=aux.get('合成設定',{})
    if type(rows) is not tuple or len(rows)>16 or type(settings) is not dict:
        raise ValueError('合成役割入力不正')
    values=tuple(能力結果を復元(r['結果']) for r in rows)
    if any(not x.成立 for x in values): raise ValueError('上流結果が不成立')
    return values,settings


class 会話能力Module:
    優先度=0
    版=会話能力版
    def __init__(self,名前): self.名前=名前
    def 判定(self,context): return 1.0
    def 実行(self,context):
        try:
            values,settings=_入力(context)
            if self.名前=='数量比較':
                if len(values)!=2: raise ValueError('左右二役割が必要')
                return 数量を比較(*values,settings)
            if self.名前=='会話回答構成':
                if '詳細' not in settings or set(settings)-{'詳細','形式','手順'}: raise ValueError('回答設定不正')
                return 回答を構成(values,**settings)
            if len(values)!=1: raise ValueError('単一の入力役割が必要')
            if self.名前=='表数量解釈': return 表数量を読む(values[0],settings)
            if self.名前=='数値記載解釈': return 記載数量を読む(values[0],settings)
            if self.名前=='会話再表現':
                if '詳細' not in settings or set(settings)-{'詳細','形式','手順'}: raise ValueError('再表現設定不正')
                return 回答を再表現(values[0],**settings)
            if self.名前=='取得報告採用':
                if settings: raise ValueError('取得採用設定は不要')
                report=values[0].データ;raw=deepcopy(report);seal=raw.pop('記録SHA256')
                if seal!=意味指紋(raw) or report['種別']!='取得報告': raise ValueError('取得報告の整合不一致')
                result=能力結果を復元(report['結果'])
                if not result.成立:
                    if result.保留理由=='外部読取未許可':
                        raise 会話処理不成立('権限不足',result.保留理由)
                    raise 会話処理不成立('取得不足',result.保留理由)
                return result
            raise ValueError('未登録の会話能力')
        except 会話処理不成立 as exc:
            return 能力結果(False,'',保留理由=str(exc))
        except (ValueError,TypeError,KeyError,AttributeError,RecursionError,OverflowError) as exc:
            return 能力結果(False,'',保留理由='会話失敗:入力不正:'+str(exc))
    def 登録(self): return 登録能力(self)


class 会話取得報告Module:
    名前='会話取得報告';版=会話能力版;優先度=0
    def __init__(self,取得器,外部許可):
        self._元=知識取得Module(取得器,外部読取許可=外部許可)
    def 判定(self,context): return self._元.判定(context)
    def 実行(self,context):
        result=self._元.実行(context)
        # 診断報告の生成成功。取得失敗を取得成功にはしない。次の採用工程が必須。
        data={'版':会話能力版,'種別':'取得報告','取得成立':result.成立,'結果':_結果辞書(result)}
        data['記録SHA256']=意味指紋(data)
        return 能力結果(True,'取得結果の診断報告',参照=result.参照,データ=data)
    def 登録(self): return 登録能力(self,外部読取=True)


def 会話能力群(取得器, *, 外部許可=False):
    names=('表数量解釈','数値記載解釈','数量比較','会話回答構成','会話再表現','取得報告採用')
    return (*tuple(会話能力Module(n).登録() for n in names),会話取得報告Module(取得器,外部許可).登録())
