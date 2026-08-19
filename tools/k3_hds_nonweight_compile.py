#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K3 pinned revision の非weight公開18 artifactを全byte実読しHDS日本語意味構文へ変換する。"""
from __future__ import annotations

import argparse, ast, base64, gzip, hashlib, json, struct, zlib
from pathlib import Path
from typing import Any
import requests

REPO='moonshotai/Kimi-K3'
REV='c5d1dd4c428bd1ce8b88c5044f3b6ccde9e3b721'
BLOCK=1024*1024

FILE_PRINCIPLE={
 '.gitattributes':'P-REPO-TRANSPORT','LICENSE':'P-LICENSE','README.md':'P-DOC',
 'assets/kimi-logo.png':'P-VISUAL-IDENTITY','config.json':'P-CONFIG',
 'configuration_kimi_k3.py':'P-CODE-CONFIG','encoding_k3.py':'P-CODE-ENCODING',
 'generation_config.json':'P-CONFIG-GENERATION','kimi_k3_processor.py':'P-CODE-PROCESSOR',
 'kimi_k3_vision_processing.py':'P-CODE-VISION','media_utils.py':'P-CODE-MEDIA',
 'model.safetensors.index.json':'P-WEIGHT-ADDRESS','modeling_kimi_k3.py':'P-CODE-MULTIMODAL',
 'modeling_kimi_linear.py':'P-CODE-LANGUAGE','preprocessor_config.json':'P-CONFIG-PREPROCESS',
 'tiktoken.model':'P-TOKEN-VOCAB','tokenization_kimi.py':'P-CODE-TOKENIZER',
 'tokenizer_config.json':'P-CONFIG-TOKENIZER',
}
PRINCIPLES={
 'P-REPO-TRANSPORT':('配布物の物理扱い条件','何が巨大/特殊ファイルを同一repoとして運搬可能にするのか','属性規則が保存・差分・LFS扱いを条件化する','属性規則を変えると同じ物理配布形態が成立しない'),
 'P-LICENSE':('利用許諾境界','何が公開物を利用可能にし、同時に利用範囲を境界づけるのか','許諾条項が利用・再配布・責任の成立条件を定める','条項を変えると許される利用関係が変わる'),
 'P-DOC':('公開説明世界','何が利用者にK3の能力・使用・評価・注意を接続するのか','説明文が実装外部の操作・理解条件を形成する','説明内容を変えると利用者が形成する操作世界が変わる'),
 'P-VISUAL-IDENTITY':('視覚識別媒体','何が配布物を視覚的に同定可能にするのか','画像byte列が復号規則を介して識別像を成立させる','画像内容または復号条件を変えると同一視覚像が成立しない'),
 'P-CONFIG':('モデル成立条件','何がK3の層数・次元・attention・MoE・量子化等の実装条件を固定するのか','設定値の関係集合がコードの具体的構成を条件化する','設定値を変えると構築されるモデル関係が変わる'),
 'P-CONFIG-GENERATION':('生成既定条件','何が生成時の既定挙動を固定するのか','生成設定が出力選択の初期条件を与える','設定を変えると同一内部状態でも生成選択条件が変わる'),
 'P-CONFIG-PREPROCESS':('視覚前処理条件','何が外部画像をvision towerへ入力可能な形へ整えるのか','前処理設定がサイズ・正規化・配置条件を固定する','条件を変えると同じ画像から形成される入力状態が変わる'),
 'P-CONFIG-TOKENIZER':('記号化条件','何が外部文字列をK3 token列へ変換する既定境界を固定するのか','tokenizer設定が特殊記号・実装・テンプレート等の記号化条件を固定する','設定を変えると同一文字列の内部住所化が変わり得る'),
 'P-CODE-CONFIG':('設定解釈実装','何が静的設定値を実行可能な構成条件へ変換するのか','設定クラスと検査規則が許容状態・層種別・既定値を成立させる','解釈規則を変えると同じ設定値から異なる構成が成立する'),
 'P-CODE-ENCODING':('対話記号構成実装','何がrole・content・thinking・tool等をtoken化前の記号列へ構成するのか','encoding規則が対話要素の順序・境界・特殊記号を形成する','構成規則を変えると同じ対話から異なるtoken前表現が成立する'),
 'P-CODE-PROCESSOR':('異種入力統合実装','何がtext/image等の外部入力を一つのモデル入力関係へ束ねるのか','processorがtokenizerとvision processingを接続し入力位置関係を形成する','統合規則を変えると同じ媒体集合から異なるモデル入力が成立する'),
 'P-CODE-VISION':('視覚前処理実装','何が画像/動画をpatch化可能な数値状態へ変換するのか','サイズ調整・正規化・patch配置規則がvision入力を成立させる','処理規則を変えると同じ媒体から異なる視覚状態が成立する'),
 'P-CODE-MEDIA':('媒体取得境界実装','何がURL/画像/動画等をprocessorが扱える媒体実体へ接続するのか','媒体読込・型分別・変換規則が外界媒体と内部処理を橋渡しする','取得/型規則を変えると同じ指定から異なる媒体状態が成立する'),
 'P-WEIGHT-ADDRESS':('重み物理住所','何がtensorの計算上の名前と96 shard上の物理所在を一意に接続するのか','weight_mapがtensor名→shardを保持し意味構造と物理分割を分離する','対応を変えると同一tensor名から正しいpayloadへ到達できない'),
 'P-CODE-LANGUAGE':('系列内部状態遷移実装','何がtoken由来状態をattention/KDA/MoE/残差を通じて次状態へ変えるのか','クラス・関数・演算接続が系列状態の保持・参照・選択・変換・帰還を成立させる','接続規則を変えると同一入力から同一状態遷移が成立しない'),
 'P-CODE-MULTIMODAL':('視覚と言語の共通状態化実装','何がvision tower出力をlanguage model系列へ接続するのか','視覚encoder・projector・placeholder位置関係が異種媒体を共通内部状態へ接続する','境界写像または位置対応を変えると同一画像の言語系列への作用が変わる'),
 'P-TOKEN-VOCAB':('記号住所表','何がbyte列を有限token住所へ対応づけるのか','mergeable byte sequenceとrankの対応が外部文字列を内部離散住所へ分節する','byte列↔rank対応を変えると同じ文字列のtoken列が変わる'),
 'P-CODE-TOKENIZER':('文字列住所化実装','何が文字列とtoken住所表を双方向に接続するのか','tokenization規則・特殊token・encode/decode処理が記号列と内部住所を接続する','規則を変えると同じ文字列/住所列の対応が変わる'),
}

def jdump(x): return json.dumps(x,ensure_ascii=False,separators=(',',':'))
def hf_url(path): return f'https://huggingface.co/{REPO}/resolve/{REV}/{path}?download=true'

def download(session,path):
 r=session.get(hf_url(path),timeout=(30,300),allow_redirects=True); r.raise_for_status(); return r.content

def git_blob_sha(data):
 h=hashlib.sha1(); h.update(f'blob {len(data)}\0'.encode()); h.update(data); return h.hexdigest()

def file_hds(path):
 pid=FILE_PRINCIPLE[path]; cw,q,p,collapse=PRINCIPLES[pid]
 return {'原理族':pid,'認知世界':cw,'原理質問':q,'開放並列場':['物理byte列','構文/形式','実行または利用時の作用関係','他artifactとの接続'],'原理分別':p,'局所適用':f'{path} の実byteと解析構造へ適用','結果帰還':'構造recordとbyte coverageを同一provenanceへ帰還','総再開放':'下流artifactとの不整合が出た場合は当該原理・境界を再開放','崩壊条件':collapse}

def line_kind(s,path):
 t=s.strip()
 if not t:return '空行'
 if path.endswith('.py'):
  if t.startswith('#'):return '注釈'
  if t.startswith(('import ','from ')):return '依存導入'
  if t.startswith(('class ','def ','async def ')):return '構造定義'
  if t.startswith(('if ','elif ','else','for ','while ','try','except','with ','match ','case ')):return '条件・制御'
  if '=' in t:return '状態/関係束縛'
  return '実行記述'
 if path.endswith('.md'):
  if t.startswith('#'):return '節境界'
  if t.startswith('```'):return 'コード境界'
  if t.startswith(('- ','* ','+ ')):return '列挙'
  if '|' in t:return '表記述'
  if '](' in t:return '参照接続'
  return '説明記述'
 if path=='LICENSE':return '利用境界記述'
 if path=='.gitattributes':return '配布属性規則'
 return 'テキスト記述'

def python_node_record(node,path,line_offsets):
 kind=type(node).__name__; name=getattr(node,'name',None)
 start=getattr(node,'lineno',None); end=getattr(node,'end_lineno',start)
 out={'kind':'python_AST意味構文','file':path,'AST型':kind,'名前':name,'開始行':start,'終了行':end}
 if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
  out['日本語意味作用']='入力引数と内部処理を一つの再利用可能な状態変換として成立させる。'
  out['引数']=[a.arg for a in node.args.args]
 elif isinstance(node,ast.ClassDef): out['日本語意味作用']='関連する状態と作用を同一実体境界へ束ねる。'
 elif isinstance(node,(ast.Assign,ast.AnnAssign,ast.AugAssign)): out['日本語意味作用']='計算結果または条件を名前付き状態へ保持・更新する。'
 elif isinstance(node,ast.Call):
  out['日本語意味作用']='別の作用を現在の処理関係へ接続する。'
  f=node.func
  if isinstance(f,ast.Name): out['呼出先']=f.id
  elif isinstance(f,ast.Attribute): out['呼出先']=f.attr
 elif isinstance(node,(ast.If,ast.Match)): out['日本語意味作用']='現在条件によって後続作用経路を分別する。'
 elif isinstance(node,(ast.For,ast.While,ast.comprehension)): out['日本語意味作用']='対象集合または条件の継続中、同型作用を反復する。'
 elif isinstance(node,(ast.Return,ast.Yield,ast.YieldFrom)): out['日本語意味作用']='形成した状態を呼出境界の外へ帰還させる。'
 elif isinstance(node,(ast.Import,ast.ImportFrom)): out['日本語意味作用']='外部実装を現在の成立条件へ接続する。'
 else: out['日本語意味作用']='当該AST構造が上位作用の局所成立要素として働く。'
 return out

def json_walk(x,path='$'):
 if isinstance(x,dict):
  for k,v in x.items(): yield from json_walk(v,path+'.'+str(k))
 elif isinstance(x,list):
  for i,v in enumerate(x): yield from json_walk(v,path+f'[{i}]')
 else: yield path,x

def printable_utf8(b):
 try:
  s=b.decode('utf-8')
  if all((c.isprintable() or c in '\t\n\r') for c in s): return s
 except Exception: pass
 return None

def parse_png(data,path,out):
 if data[:8]!=b'\x89PNG\r\n\x1a\n': raise ValueError('bad PNG signature')
 pos=8; chunks=[]
 while pos<len(data):
  if pos+12>len(data): raise ValueError('truncated PNG chunk')
  n=struct.unpack('>I',data[pos:pos+4])[0]; typ=data[pos+4:pos+8].decode('ascii','replace'); end=pos+12+n
  if end>len(data): raise ValueError('PNG chunk overflow')
  payload=data[pos+8:pos+8+n]; crc_expected=struct.unpack('>I',data[pos+8+n:end])[0]; crc_actual=zlib.crc32(data[pos+4:pos+8+n])&0xffffffff
  rec={'kind':'PNGチャンク意味構文','file':path,'chunk':typ,'byte_range':[pos,end],'payload_bytes':n,'chunk_sha256':hashlib.sha256(data[pos:end]).hexdigest(),'CRC一致':crc_expected==crc_actual,'日本語意味作用':'PNG復号に必要な構造/画像データを物理的に保持する。'}
  if typ=='IHDR' and n==13:
   w,h,bd,ct,comp,filt,inter=struct.unpack('>IIBBBBB',payload); rec.update({'width':w,'height':h,'bit_depth':bd,'color_type':ct,'interlace':inter})
  out.write(jdump(rec)+'\n'); chunks.append((pos,end)); pos=end
  if typ=='IEND': break
 if pos!=len(data): raise ValueError(f'PNG trailing bytes {len(data)-pos}')
 return len(chunks)

def compile_file(meta,data,out):
 path=meta['path']; hds=file_hds(path)
 out.write(jdump({'kind':'artifact_HDS','file':path,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'HDS':hds})+'\n')
 # すべてのbyteを重複なし固定blockへ所属させる
 for a in range(0,len(data),BLOCK):
  b=min(a+BLOCK,len(data)); seg=data[a:b]
  out.write(jdump({'kind':'byte_coverage','file':path,'byte_range':[a,b],'sha256':hashlib.sha256(seg).hexdigest(),'日本語意味':'この区間は当該artifactの原データを保持し、同fileのHDS構造recordへ接続される。'})+'\n')
 structural=0
 if path=='model.safetensors.index.json':
  x=json.loads(data); out.write(jdump({'kind':'weight_index_metadata','file':path,'metadata':x.get('metadata',{}),'日本語意味':'全tensor payload総量と物理分割の上位条件。'})+'\n'); structural+=1
  for name,shard in x['weight_map'].items():
   out.write(jdump({'kind':'tensor物理住所','file':path,'tensor':name,'shard':shard,'日本語意味構文':f'{name} の計算上の名前を {shard} 上の物理payloadへ接続する。意味住所と物理分割は同一視しない。'})+'\n'); structural+=1
 elif path=='tiktoken.model':
  off=0
  for i,line in enumerate(data.splitlines(keepends=True)):
   raw=line.rstrip(b'\r\n'); parts=raw.split()
   if len(parts)!=2: raise ValueError(f'bad tiktoken line {i+1}')
   tok=base64.b64decode(parts[0]); rank=int(parts[1]); end=off+len(line)
   out.write(jdump({'kind':'token住所意味構文','file':path,'line':i+1,'source_byte_range':[off,end],'source_line_sha256':hashlib.sha256(line).hexdigest(),'rank':rank,'token_bytes_hex':tok.hex(),'UTF8表示':printable_utf8(tok),'日本語意味構文':f'byte列をtoken住所 {rank} へ対応づけ、外部記号列を有限の内部離散住所へ分節する。'})+'\n'); structural+=1; off=end
  if off!=len(data): raise ValueError('token byte coverage mismatch')
 elif path.endswith('.json'):
  x=json.loads(data)
  for jp,v in json_walk(x):
   out.write(jdump({'kind':'JSON設定意味構文','file':path,'JSONPath':jp,'値':v,'日本語意味構文':'この値が当該JSONPathで実装または前処理の局所条件を固定する。上位HDS原理はartifact_HDSを参照。'})+'\n'); structural+=1
 elif path.endswith('.py'):
  text=data.decode('utf-8'); tree=ast.parse(text,filename=path)
  for node in ast.walk(tree): out.write(jdump(python_node_record(node,path,None))+'\n'); structural+=1
  off=0
  for i,line in enumerate(data.splitlines(keepends=True)):
   end=off+len(line); s=line.decode('utf-8','replace')
   out.write(jdump({'kind':'source_line_coverage','file':path,'line':i+1,'byte_range':[off,end],'sha256':hashlib.sha256(line).hexdigest(),'日本語意味分類':line_kind(s,path)})+'\n'); structural+=1; off=end
  if off!=len(data): raise ValueError('source line byte coverage mismatch')
 elif path.endswith('.png'):
  structural+=parse_png(data,path,out)
 else:
  off=0
  for i,line in enumerate(data.splitlines(keepends=True)):
   end=off+len(line); s=line.decode('utf-8','replace')
   out.write(jdump({'kind':'text_line意味構文','file':path,'line':i+1,'byte_range':[off,end],'sha256':hashlib.sha256(line).hexdigest(),'日本語意味分類':line_kind(s,path),'日本語意味構文':'この記述は当該artifactの上位原理を局所的に成立・説明・境界化する記述単位として保持する。'})+'\n'); structural+=1; off=end
  if off!=len(data): raise ValueError('text line byte coverage mismatch')
 return structural

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--inventory',type=Path,required=True); ap.add_argument('--out',type=Path,required=True); ap.add_argument('--audit',type=Path,required=True); a=ap.parse_args()
 inv=json.loads(a.inventory.read_text(encoding='utf-8')); metas=inv['nonweight_files']; expected_paths=[m['path'] for m in metas]
 if set(expected_paths)!=set(FILE_PRINCIPLE): raise ValueError({'missing_mapping':sorted(set(expected_paths)-set(FILE_PRINCIPLE)),'extra_mapping':sorted(set(FILE_PRINCIPLE)-set(expected_paths))})
 s=requests.Session(); a.out.parent.mkdir(parents=True,exist_ok=True); audits=[]; total=0; structural=0
 with gzip.open(a.out,'wt',encoding='utf-8') as out:
  for meta in metas:
   path=meta['path']; data=download(s,path); size_ok=len(data)==int(meta['size']); sha256=hashlib.sha256(data).hexdigest(); lfs=meta.get('lfs');
   if lfs and isinstance(lfs,dict) and lfs.get('sha256'): identity_ok=sha256==lfs['sha256']; identity_kind='lfs_sha256'
   else: identity_ok=git_blob_sha(data)==meta.get('blob_id'); identity_kind='git_blob_sha1'
   if not size_ok or not identity_ok: raise ValueError({'path':path,'size_ok':size_ok,'identity_ok':identity_ok,'identity_kind':identity_kind})
   n=compile_file(meta,data,out); structural+=n; total+=len(data); audits.append({'path':path,'bytes':len(data),'sha256':sha256,'size_match':size_ok,'identity_match':identity_ok,'identity_kind':identity_kind,'HDS原理族':FILE_PRINCIPLE[path],'structure_records':n,'byte_coverage_blocks':(len(data)+BLOCK-1)//BLOCK})
   print(jdump({'processed':path,'bytes':len(data),'structure_records':n}),flush=True)
   del data
 expected_total=int(inv['nonweight_file_size'])
 report={'repo':REPO,'revision':REV,'mother_set_manifest_sha256':inv['manifest_sha256'],'expected_nonweight_files':len(metas),'processed_nonweight_files':len(audits),'expected_nonweight_bytes':expected_total,'processed_nonweight_bytes':total,'unprocessed_nonweight_files':sorted(set(expected_paths)-{r['path'] for r in audits}),'unprocessed_nonweight_bytes':expected_total-total,'HDS適合不能artifact数':sum(1 for r in audits if not r['HDS原理族']),'structure_records':structural,'files':audits}
 report['PASS_NONWEIGHT_FULL_COMPILE']=(report['processed_nonweight_files']==report['expected_nonweight_files'] and report['unprocessed_nonweight_bytes']==0 and not report['unprocessed_nonweight_files'] and report['HDS適合不能artifact数']==0 and all(r['size_match'] and r['identity_match'] for r in audits))
 a.audit.parent.mkdir(parents=True,exist_ok=True); a.audit.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8'); print(json.dumps({k:report[k] for k in ('expected_nonweight_files','processed_nonweight_files','expected_nonweight_bytes','processed_nonweight_bytes','unprocessed_nonweight_bytes','HDS適合不能artifact数','structure_records','PASS_NONWEIGHT_FULL_COMPILE')},ensure_ascii=False,indent=2)); return 0 if report['PASS_NONWEIGHT_FULL_COMPILE'] else 2
if __name__=='__main__': raise SystemExit(main())
