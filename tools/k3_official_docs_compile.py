#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K3公式GitHub + Kimi公式Tech Blogの全公開資料を全byte実読しHDS日本語意味構文化する。

対象境界:
- MoonshotAI/Kimi-K3 pinned commit の全file（再帰tree）
- READMEが直接指す https://www.kimi.com/blog/kimi-k3 の取得時点HTML
- 当該blog本文DOMが直接参照する kimi/moonshot 配下の画像媒体

PDFは全原byte coverageに加え、全page/text block/image objectを構造観測する。
HTMLは全原byte coverageに加え、見出し/本文/表/リスト等のDOM意味単位を全数観測する。
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import re
import struct
import time
import urllib.parse
import zlib
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import fitz  # PyMuPDF
import requests
from bs4 import BeautifulSoup
from PIL import Image

GH_REPO='MoonshotAI/Kimi-K3'
GH_COMMIT='3cb39dfd32e51c3328e2e4b4af21341247d06c43'
BLOG_URL='https://www.kimi.com/blog/kimi-k3'
BLOCK=1024*1024

PRINCIPLES={
 'P-RELEASE-LICENSE':('公開利用境界','何がK3公開物の利用・再配布・責任境界を成立させるのか','ライセンス条項が公開利用可能性と禁止/責任条件を同時に定める','条項を変えると許容利用関係が変わる'),
 'P-RELEASE-DOC':('公開操作・理解世界','何がK3の構造・利用・能力・制約を外部利用者へ接続するのか','README記述がモデル実体と利用手順・評価・制約の間の参照関係を形成する','説明または参照先を変えると外部利用者の操作条件が変わる'),
 'P-RELEASE-VISUAL':('公開視覚識別媒体','何がK3公開物を視覚的に識別可能にするのか','画像符号と復号規則がK3の視覚識別像を成立させる','画像byteまたは復号規則を変えると同一視覚像が成立しない'),
 'P-REPORT-OVERVIEW':('K3全体成立構造','何がK3を2.8T級・multimodal・agentic modelとして成立させているのか','architecture・training・post-training・infrastructure・evaluationの相互関係がK3全体を成立させる','いずれかの主要成立関係を変えると同じK3全体像は成立しない'),
 'P-REPORT-ARCH':('モデル内部情報流','何がtoken・depth・width・visionの情報流をK3内部で成立させるのか','KDA/Gated MLA・AttnRes・Stable LatentMoE・MoonViT経路が異なる軸の情報流を分担し接続する','接続比・残差選択・expert選択・媒体境界を変えると同じ内部状態遷移は成立しない'),
 'P-REPORT-KDA':('系列状態保持・更新','何が長系列で旧状態を保持/忘却しつつ現在入力を書き込み参照するのか','channel-wise decay α、write strength β、Q/K/V、recurrent state Sの関係がKDA状態遷移を成立させる','decay/update/参照関係を変えると同じ系列履歴から同じ次状態は成立しない'),
 'P-REPORT-ATTNRES':('深度方向の状態再選択','何が直前層だけでなくembeddingと先行block群から必要状態を再選択するのか','learned pseudo-queryと候補状態score/softmax混合が深度方向の選択的帰還を成立させる','候補集合またはscore関係を変えると同じ深度情報流は成立しない'),
 'P-REPORT-MOE':('状態依存専門変換','何が896 expertから局所的に16を選び巨大幅を計算可能にするのか','router適合関係・latent境界・shared/routed expertの組合せが疎な専門変換を成立させる','router/latent/expert対応を変えると同じ専門作用集合が成立しない'),
 'P-REPORT-VISION':('視覚と言語の共通状態化','何が画像/動画を言語backboneと同じ系列処理へ接続するのか','MoonViT-V2による視覚状態形成とprojectorによる共有embedding境界が異種媒体接続を成立させる','視覚encoderまたは境界写像を変えると同じ媒体作用は成立しない'),
 'P-REPORT-PRETRAIN':('基礎能力形成過程','何が初期K3の広域能力分布を形成するのか','text/vision corpusの選別・再構成・samplingと段階的context拡張、最適化条件の帰還が基礎状態を形成する','data関係・sampling・training条件を変えると形成される能力分布が変わる'),
 'P-REPORT-POSTTRAIN':('行動・推論方策形成','何が基礎modelを長期agentic行動・複数reasoning effortへ局所適応させ統合するのか','SFT→domain/effort別RL→multi-teacher on-policy distillationの循環が専門方策形成と統合を成立させる','環境・報酬・teacher統合関係を変えると同じ行動方策は成立しない'),
 'P-REPORT-INFRA':('巨大model実行成立条件','何が3T級・1M context・長期rolloutを有限hardware上で訓練/推論可能にするのか','KDA kernel/CP・expert parallelism・memory/communication overlap・persistent sandbox/cache/schedulingが物理実行を成立させる','並列・memory・state保持・通信条件を変えると同一規模の実行成立性が崩れる'),
 'P-REPORT-EVAL':('外部能力観測関係','何がK3内部能力をbenchmark上の観測値へ接続するのか','task・harness・reasoning effort・verifier・score条件の組が能力を局所観測値として成立させる','評価条件を変えると同一能力でも観測値の意味が変わる'),
 'P-REPORT-LIMIT':('成立境界・破綻条件','何がK3の安定運用を壊し得るか','thinking history・proactiveness・harness等の条件が能力発現の境界を形成する','境界条件を外すと同一weightでも出力安定性/制御性が変わる'),
 'P-REPORT-REFERENCE':('外部知識参照関係','何がK3報告内の主張を先行研究・外部資料へ接続するのか','引用住所が主張と外部成立根拠/比較対象を接続する','参照先を失うと出典追跡可能性が崩れる'),
 'P-BLOG-INTRO':('公開時点K3位置づけ','何がK3を公開frontier modelとして提示しているのか','model規模・architecture・能力・公開状態の説明が外部のK3認知世界を形成する','公開状態/仕様記述を変えると同じ位置づけは成立しない'),
 'P-BLOG-CODING':('長期coding能力の公開観測','何がK3 coding能力を具体例・benchmarkへ接続するのか','kernel/compiler/game/chip/research等のtask実行記録が能力主張を具体的作用へ接続する','task条件/検証条件を変えると観測された能力意味が変わる'),
 'P-BLOG-KNOWLEDGE':('knowledge work能力の公開観測','何が調査・可視化・dashboard・動画編集能力を具体成果へ接続するのか','長期tool利用とmultimodal成果物の事例がknowledge work能力を観測可能にする','入力資料・tool・評価境界を変えると同一成果主張は成立しない'),
 'P-BLOG-ARCH':('architecture公開説明','何がKDA/AttnRes/LatentMoE/QAT等をK3の効率・安定性へ接続するのか','各機構とtraining/deployment条件の関係記述が公開architecture像を形成する','機構または接続条件を変えると同じ効率説明は成立しない'),
 'P-BLOG-AVAIL':('利用可能性境界','何が公開K3をagent/work/code/APIとして利用可能にするのか','提供channel・version・API条件が外部利用経路を成立させる','提供条件を変えると同じ利用可能性は成立しない'),
 'P-BLOG-EVAL':('benchmark公開観測条件','何が公開scoreを比較可能な局所観測として成立させるのか','harness・effort・task version・judge・run条件がscoreの意味を条件化する','評価条件を変えるとscoreを同一意味で比較できない'),
 'P-BLOG-LIMIT':('公開運用境界','何がK3出力の不安定化/過剰自律を生む条件として明示されるのか','thinking-history保持・model switch・曖昧意図・system constraintsが安定運用境界を形成する','境界条件を満たさないと同一weightでも品質/制御が崩れる'),
}


def jdump(x:Any)->str:return json.dumps(x,ensure_ascii=False,separators=(',',':'))

def git_blob_sha(data:bytes)->str:
 h=hashlib.sha1(); h.update(f'blob {len(data)}\0'.encode()); h.update(data); return h.hexdigest()

def hds(pid:str,local:str,result:str='観測構造を同一provenanceへ帰還'):
 cw,q,disc,collapse=PRINCIPLES[pid]
 return {'認知世界':cw,'原理質問':q,'開放並列場':['物理表現','構造/記号表現','実行/利用時の作用','別解釈・反例・境界条件'],'原理分別':disc,'局所適用':local,'結果帰還':result,'総再開放':'下流観測との不整合・反例・新公開版が観測された場合は原理・境界・出典を再開放','崩壊条件':collapse}

def byte_coverage(out,source_id:str,data:bytes):
 for a in range(0,len(data),BLOCK):
  b=min(a+BLOCK,len(data)); seg=data[a:b]
  out.write(jdump({'kind':'byte_coverage','source_id':source_id,'byte_range':[a,b],'sha256':hashlib.sha256(seg).hexdigest(),'日本語意味':'この原byte区間は当該公開artifactの物理表現として欠落なく観測済み。上位HDS意味構造へprovenance接続する。'})+'\n')

def report_principle(page:int,text:str)->str:
 t=text.lower()
 if page>=34 or re.search(r'\breferences\b',t):return 'P-REPORT-REFERENCE'
 if 'limitation' in t:return 'P-REPORT-LIMIT'
 if page<=1:return 'P-REPORT-OVERVIEW'
 if page<=9:
  if 'kimi delta attention' in t or 'decay' in t or 'kda' in t:return 'P-REPORT-KDA'
  if 'attention residual' in t or 'attnres' in t:return 'P-REPORT-ATTNRES'
  if 'moe' in t or 'expert' in t:return 'P-REPORT-MOE'
  if 'vision' in t or 'moonvit' in t:return 'P-REPORT-VISION'
  return 'P-REPORT-ARCH'
 if page<=11:return 'P-REPORT-PRETRAIN'
 if page<=16:return 'P-REPORT-POSTTRAIN'
 if page<=22:return 'P-REPORT-INFRA'
 if page<=33:return 'P-REPORT-EVAL'
 return 'P-REPORT-REFERENCE'

def compile_pdf(out,source_id:str,data:bytes):
 doc=fitz.open(stream=data,filetype='pdf')
 records=0; image_xrefs=set()
 out.write(jdump({'kind':'PDF_HDS','source_id':source_id,'pages':doc.page_count,'HDS':hds('P-REPORT-OVERVIEW',f'{doc.page_count}頁technical report全体をarchitecture/training/post-training/infrastructure/evaluation/limitsの成立関係として開放')})+'\n');records+=1
 for pno in range(doc.page_count):
  page=doc[pno]; text=page.get_text('text'); blocks=page.get_text('blocks')
  pid=report_principle(pno,text)
  out.write(jdump({'kind':'PDF_page_HDS','source_id':source_id,'page':pno+1,'text_sha256':hashlib.sha256(text.encode()).hexdigest(),'text_chars':len(text),'HDS原理族':pid,'HDS':hds(pid,f'page {pno+1} の全text/image/layout観測へ適用'),'日本語意味構文':PRINCIPLES[pid][2]})+'\n');records+=1
  for bi,b in enumerate(blocks):
   x0,y0,x1,y1,txt,*rest=b
   if not str(txt).strip():continue
   pidb=report_principle(pno,str(txt))
   out.write(jdump({'kind':'PDF_text_block_HDS','source_id':source_id,'page':pno+1,'block':bi,'bbox':[x0,y0,x1,y1],'原文':str(txt),'HDS原理族':pidb,'日本語意味構文':PRINCIPLES[pidb][2],'崩壊条件':PRINCIPLES[pidb][3]})+'\n');records+=1
  for im in page.get_images(full=True):
   xref=int(im[0]); image_xrefs.add(xref)
   out.write(jdump({'kind':'PDF_page_image_reference','source_id':source_id,'page':pno+1,'xref':xref,'width':im[2],'height':im[3],'colorspace':im[5],'日本語意味':'図表・画像として本文の関係記述を視覚構造へ射影する媒体。画像object本体はxref単位で別recordに全数観測。'})+'\n');records+=1
 for xref in sorted(image_xrefs):
  info=doc.extract_image(xref); raw=info.get('image',b'')
  out.write(jdump({'kind':'PDF_embedded_image','source_id':source_id,'xref':xref,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'ext':info.get('ext'),'width':info.get('width'),'height':info.get('height'),'日本語意味':'technical report内の視覚観測媒体。原PDF byte coverageとは独立に復号後image object identityを保持。'})+'\n');records+=1
 return {'pages':doc.page_count,'embedded_images':len(image_xrefs),'records':records}

def compile_png(out,source_id:str,data:bytes):
 try:
  im=Image.open(io.BytesIO(data)); im.load(); meta={'format':im.format,'width':im.width,'height':im.height,'mode':im.mode}
 except Exception as e: meta={'decode_error':repr(e)}
 out.write(jdump({'kind':'image_HDS','source_id':source_id,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'image':meta,'HDS':hds('P-RELEASE-VISUAL','公開画像の全byteと復号後寸法・modeへ適用')})+'\n')
 return {'records':1,**meta}

def compile_text(out,source_id:str,path:str,data:bytes,pid:str):
 text=data.decode('utf-8'); off=0; n=0
 out.write(jdump({'kind':'text_artifact_HDS','source_id':source_id,'HDS':hds(pid,f'{path} 全文へ適用')})+'\n');n+=1
 for li,line in enumerate(data.splitlines(keepends=True),1):
  end=off+len(line); s=line.decode('utf-8','replace')
  out.write(jdump({'kind':'text_line_HDS','source_id':source_id,'line':li,'byte_range':[off,end],'sha256':hashlib.sha256(line).hexdigest(),'原文':s.rstrip('\r\n'),'日本語意味構文':PRINCIPLES[pid][2],'HDS原理族':pid})+'\n'); n+=1;off=end
 if off!=len(data):raise ValueError('text coverage mismatch')
 return {'records':n,'lines':li if data else 0}

def gh_tree(session:requests.Session):
 url=f'https://api.github.com/repos/{GH_REPO}/git/trees/{GH_COMMIT}?recursive=1'; r=session.get(url,timeout=60);r.raise_for_status(); tree=r.json()['tree']
 return sorted([x for x in tree if x['type']=='blob'],key=lambda x:x['path'])

def blog_pid(heading:str)->str:
 h=heading.lower()
 if 'coding' in h or any(x in h for x in ('kernel','compiler','game','chip')):return 'P-BLOG-CODING'
 if 'knowledge' in h or any(x in h for x in ('research','widget','dashboard','video')):return 'P-BLOG-KNOWLEDGE'
 if 'architecture' in h or 'infrastructure' in h or '3t-class' in h:return 'P-BLOG-ARCH'
 if 'availability' in h:return 'P-BLOG-AVAIL'
 if 'benchmark' in h or 'footnote' in h:return 'P-BLOG-EVAL'
 if 'limitation' in h:return 'P-BLOG-LIMIT'
 return 'P-BLOG-INTRO'

def compile_blog(session,out):
 r=session.get(BLOG_URL,timeout=90,headers={'User-Agent':'Mozilla/5.0 K3-HDS-Compiler/6.0'});r.raise_for_status();data=r.content;source_id='kimi-blog:current:'+BLOG_URL
 byte_coverage(out,source_id,data)
 soup=BeautifulSoup(data,'html.parser'); root=soup.find('main') or soup.find('article') or soup.body or soup
 current='Kimi K3'; records=0; text_units=0
 out.write(jdump({'kind':'web_artifact_HDS','source_id':source_id,'retrieved_unix':time.time(),'status_code':r.status_code,'content_type':r.headers.get('content-type'),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'HDS':hds('P-BLOG-INTRO','K3 Tech Blog取得時点HTML全体へ適用')})+'\n');records+=1
 for el in root.find_all(['h1','h2','h3','h4','p','li','figcaption','th','td']):
  txt=' '.join(el.stripped_strings)
  if not txt:continue
  if el.name in ('h1','h2','h3','h4'):current=txt
  pid=blog_pid(current)
  out.write(jdump({'kind':'blog_DOM_HDS','source_id':source_id,'tag':el.name,'section':current,'原文':txt,'HDS原理族':pid,'日本語意味構文':PRINCIPLES[pid][2],'崩壊条件':PRINCIPLES[pid][3]})+'\n');records+=1;text_units+=1
 media=[]
 for img in root.find_all('img'):
  src=img.get('src') or img.get('data-src')
  if not src:continue
  u=urllib.parse.urljoin(BLOG_URL,src)
  host=urllib.parse.urlparse(u).hostname or ''
  if ('moonshot' in host or 'kimi' in host) and u not in media:media.append(u)
 media_results=[]
 for i,u in enumerate(media):
  try:
   rr=session.get(u,timeout=120,headers={'User-Agent':'Mozilla/5.0 K3-HDS-Compiler/6.0'});rr.raise_for_status();raw=rr.content
   try:
    im=Image.open(io.BytesIO(raw));im.load();m={'format':im.format,'width':im.width,'height':im.height,'mode':im.mode}
   except Exception as e:m={'decode_error':repr(e)}
   mid=f'kimi-blog-media:{i}:{u}';byte_coverage(out,mid,raw)
   out.write(jdump({'kind':'blog_media_HDS','source_id':mid,'parent':source_id,'url':u,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'image':m,'HDS':hds('P-RELEASE-VISUAL','K3 Tech Blog本文が直接参照する視覚媒体の全byteへ適用')})+'\n');records+=1
   media_results.append({'url':u,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),**m})
  except Exception as e:media_results.append({'url':u,'error':repr(e)})
 return {'source_id':source_id,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'text_units':text_units,'media_count':len(media),'media':media_results,'records':records,'retrieved_at_unix':time.time()}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);ap.add_argument('--audit',type=Path,required=True);ap.add_argument('--mother',type=Path,required=True);a=ap.parse_args()
 s=requests.Session();tree=gh_tree(s);a.out.parent.mkdir(parents=True,exist_ok=True);audit=[];total_gh=0;records=0
 with open(a.out,'wt',encoding='utf-8') as out:
  for meta in tree:
   path=meta['path'];url=f'https://raw.githubusercontent.com/{GH_REPO}/{GH_COMMIT}/{path}';r=s.get(url,timeout=180);r.raise_for_status();data=r.content
   if len(data)!=int(meta['size']) or git_blob_sha(data)!=meta['sha']:raise ValueError({'path':path,'expected_size':meta['size'],'got':len(data),'expected_blob':meta['sha'],'got_blob':git_blob_sha(data)})
   sid=f'github:{GH_REPO}@{GH_COMMIT}:{path}';byte_coverage(out,sid,data)
   if path.endswith('.pdf'):detail=compile_pdf(out,sid,data);pid='P-REPORT-OVERVIEW'
   elif path.lower().endswith(('.png','.jpg','.jpeg','.webp')):detail=compile_png(out,sid,data);pid='P-RELEASE-VISUAL'
   elif path=='LICENSE':detail=compile_text(out,sid,path,data,'P-RELEASE-LICENSE');pid='P-RELEASE-LICENSE'
   else:detail=compile_text(out,sid,path,data,'P-RELEASE-DOC');pid='P-RELEASE-DOC'
   records+=detail.get('records',0);total_gh+=len(data);audit.append({'path':path,'bytes':len(data),'git_blob_sha1':meta['sha'],'sha256':hashlib.sha256(data).hexdigest(),'HDS原理族':pid,'detail':detail})
   del data
  blog=compile_blog(s,out);records+=blog['records']
 mother={'sources':{'github':{'repo':GH_REPO,'commit':GH_COMMIT,'files':audit,'file_count':len(audit),'bytes':total_gh},'tech_blog':blog},'logical_scope':'K3公式GitHub pinned commit全file + README直結K3 Tech Blog本文HTML + 本文直結Kimi/Moonshot画像媒体','generated_at_unix':time.time()}
 # Blog media bytes are distinct public artifacts; failed downloads remain unprocessed.
 blog_media_ok=[m for m in blog['media'] if 'error' not in m];blog_media_fail=[m for m in blog['media'] if 'error' in m]
 expected_items=len(audit)+1+len(blog['media']);processed_items=len(audit)+1+len(blog_media_ok)
 expected_bytes=total_gh+blog['bytes']+sum(int(m.get('bytes',0)) for m in blog['media'])
 processed_bytes=total_gh+blog['bytes']+sum(int(m.get('bytes',0)) for m in blog_media_ok)
 report={'github':{'expected_files':len(tree),'processed_files':len(audit),'bytes':total_gh},'tech_blog':blog,'expected_items':expected_items,'processed_items':processed_items,'expected_bytes_from_observed_manifest':expected_bytes,'processed_bytes':processed_bytes,'unprocessed_items':expected_items-processed_items,'unprocessed_bytes':expected_bytes-processed_bytes,'media_failures':blog_media_fail,'HDS適合不能':0,'semantic_records':records}
 report['PASS_OFFICIAL_DOCS_FULL_COMPILE']=(len(tree)==len(audit) and not blog_media_fail and report['unprocessed_items']==0 and report['unprocessed_bytes']==0)
 a.audit.parent.mkdir(parents=True,exist_ok=True);a.audit.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');a.mother.parent.mkdir(parents=True,exist_ok=True);a.mother.write_text(json.dumps(mother,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({'github_files':len(audit),'github_bytes':total_gh,'blog_bytes':blog['bytes'],'blog_text_units':blog['text_units'],'blog_media':blog['media_count'],'unprocessed_items':report['unprocessed_items'],'unprocessed_bytes':report['unprocessed_bytes'],'semantic_records':records,'PASS':report['PASS_OFFICIAL_DOCS_FULL_COMPILE']},ensure_ascii=False,indent=2))
 return 0 if report['PASS_OFFICIAL_DOCS_FULL_COMPILE'] else 2
if __name__=='__main__':raise SystemExit(main())
