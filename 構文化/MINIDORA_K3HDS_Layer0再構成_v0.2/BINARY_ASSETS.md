# v0.2 大容量成果物台帳

## 生成済み成果物

- `MINIDORA_K3HDS_Layer0再構成_v0_2_core.zip`
  - SHA-256: `9f3748987751f0bbc714b056f19f37ef5195ecc184738d21922179afae7b2214`
- `MINIDORA_K3HDS_Layer0再構成_v0_2_selfcontained.zip`
  - SHA-256: `32e7f5423ce9c0b159cd97692f10d30df445d4c0444228f021f4a5f2f73fa9f8`
- 入力 `K3_HDS日本語翻訳データ_全量_v6_1.zip`
  - SHA-256: `c861a891835d9a11894a4225ca210ca151058cad1e957b71b1ae453dc7f89fef`

## Core内の大容量生成物

- `05_Adapter/token住所互換表.jsonl.gz`
  - bytes: `11101122`
  - SHA-256: `443ca45205a8733ea84374ce34ae761532830fa53d361c79ad35831d322d5846`
- `07_由来/全量ルーティング索引.jsonl.gz`
  - bytes: `51908236`
  - SHA-256: `9016b1888a6907d23e2fc59c8d8ee3517c31508a4cc222ef51adb062c7327d9b`

## 保存境界

2026-08-20時点のChatGPT GitHubコネクタは、ローカル大容量バイナリをGitHub Release assetへ直接アップロードする操作を公開していない。このため本コミットではLayer-0/Pの正本ロジック・契約・監査をGitへ保存し、上記大容量バイナリはSHA台帳で固定する。

大容量2索引およびZIP本体がGitHub Releaseへ保存されるまでは、`完全バイナリ保存`とは判定しない。
