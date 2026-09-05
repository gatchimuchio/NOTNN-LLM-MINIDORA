# GLM還元 — 参照計画・並列作業状態・多時間尺度 v1

状態: **実験・構文化資産（active Coreではない）**  
旧本文保存先: `実験/33_GLM還元_参照計画と並列作業状態_v1.md`

この文書が以前「現行標準経路」と記述していたV3 / adaptive arbitration / J経路は、2026-09-05の独立監査で `32_MINIDORA_HDS監督介入制御_v1.md` の責任境界と衝突することが確認されたため、active Coreから隔離した。

GLM由来の構文化成果自体は破棄しない。次の条件を満たす一般作用だけをCoreへ個別還元する。

- benchmark固有でない
- 既存APPROVEを破壊しない
- `selected -> executed -> state changed -> downstream consumed` を実測できる
- HDSへ回答ラベル・候補本文・候補得点を逆流させない
- final COMMIT権限を候補生成/監督へ移さない

現行active Coreは `32_MINIDORA_HDS監督介入制御_v1.md` と `docs/CORE_FREEZE_CANDIDATE_2026-09-05.md` に従う。
