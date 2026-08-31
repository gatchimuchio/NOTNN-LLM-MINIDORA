# Branch統廃合記録 — 2026-09-01

2026-09-01時点で、開発正本を `main` 一本へ集約した。

削除前に存在したmain以外のbranchを、tip commitとmain包含状態付きで記録する。未包含branchは旧実験・旧設計・benchmark局所実験として採用せず、現行最小汎用LLM coreへ無条件統合しない。必要な一般作用が将来必要になった場合は、現行正本から再導出する。

| branch | tip | main包含 |
|---|---|---|
| `bench/hds-v1-adaptive-selection` | `6d94b25b48cb29624a27e9f0fd7cf909b265ec54` | 包含済み |
| `chappie/auxiliary-endpoint-clean-v12` | `041ddaec4750f45a56c70500fb00e5adbbd1e855` | 未包含・未採用 |
| `chappie/bench-multilingual-trinity-20260821` | `9dedec3875ff04d8afb1a3751c78e15ef3efc099` | 未包含・未採用 |
| `chappie/classification-clean-v10` | `8232139af64e631fc358af785e68628d3c7d48e5` | 未包含・未採用 |
| `chappie/classification-current-v14` | `db4f7555a7acc1f7c787a96d6d1926e3c7a060e0` | 未包含・未採用 |
| `chappie/comparison-clean-v07` | `199332e1ddec990a3958f07fe4ea3809e5d1f26f` | 未包含・未採用 |
| `chappie/compiler-runtime-projection-v15` | `66a0be45df7ff28dfe2bb7c00e4a95fbd84ef82a` | 未包含・未採用 |
| `chappie/current-main-baseline-20260824` | `7c3c78de07898eccf9929cd0a7508e3d26d593ef` | 未包含・未採用 |
| `chappie/fix-pr35-ablation-merge` | `5f4d8d0537811f7034fa79d8a189432e4ad52b37` | 包含済み |
| `chappie/gpqa-improve-v0-5` | `00fe810c2a2c41bb00c4a0a95c9623528db5c67e` | 包含済み |
| `chappie/gpqa-science-only-audit` | `3881b03c4c313aa04ff213205a72a3e2d1ad83e1` | 未包含・未採用 |
| `chappie/gpqa-v06-result-log` | `3f08cfeb80e7cba8b4e490e4a881ec63da3eaf8e` | 未包含・未採用 |
| `chappie/hds-compiler-architecture-v1` | `2441297c2255ec9682f5b2c0ed13e4f4fb042f06` | 包含済み |
| `chappie/hds-compiler-v1-1` | `3f8938b3310229924cbcdfad670b7374d8143e4e` | 包含済み |
| `chappie/hds-compiler-v1-2` | `89db22205329089f5dbd66b75858cd6801bb7c53` | 包含済み |
| `chappie/hds-data-to-k-20260822` | `eadfaa9bd861651977cd45a60ff11b8cdcc6de6b` | 未包含・未採用 |
| `chappie/hds-gpqa-semantic-20260822` | `5ac4a932450a50eb02f4bbc60c378e6f61250229` | 包含済み |
| `chappie/hds-ir-compiler-20260821` | `255da457adf360e183f183d6adce47500e81a6a1` | 包含済み |
| `chappie/hds-ir-compiler-v2-20260821` | `255da457adf360e183f183d6adce47500e81a6a1` | 包含済み |
| `chappie/hds-ir-native-k3-20260822` | `8cfe8142f053f1314fcb145d20790d91b4c15fdc` | 未包含・未採用 |
| `chappie/hds-ir-public-boundary-20260821` | `255da457adf360e183f183d6adce47500e81a6a1` | 包含済み |
| `chappie/hds-slot-r-v1` | `dbecc99fd1a4d4b488e16e76014c597e2ebd50ef` | 包含済み |
| `chappie/k3-functional-equivalence-20260821` | `b46167e76c0ba6f4da8f18eead33fa31948c67f0` | 未包含・未採用 |
| `chappie/language-base-p-v02` | `4fa0a9495198825f8d30b7022bd33b93be414b0b` | 未包含・未採用 |
| `chappie/language-semantic-bridge-v03` | `36d8859ac6ec02a0c18bde055df224ee530a855c` | 未包含・未採用 |
| `chappie/macos-benchmark-smoke` | `e940c8fc8a09cdcdb2ef0954872e812ad646b04c` | 包含済み |
| `chappie/minidora-performance-v0-4` | `8cddbd43ececee8e26ad5a2fff966cf31c1b6e7c` | 包含済み |
| `chappie/minidora-polish-20260822` | `d41ca72a8af3cd15e89c26b9a8a6858909c9669f` | 未包含・未採用 |
| `chappie/multilingual-trinity-context-20260821` | `5ac4a932450a50eb02f4bbc60c378e6f61250229` | 包含済み |
| `chappie/natural-comparison-v07` | `a09ead6684f2e092ddc567d7a37de1521c42b069` | 未包含・未採用 |
| `chappie/natural-language-io-20260821` | `35d0798679e94da931e4a019f0df1487c26c35c9` | 包含済み |
| `chappie/open-relation-structural-priority-v16` | `be647ead8eca1b1a840ae633c1481858500c88cd` | 未包含・未採用 |
| `chappie/perf-brushup-v0-6` | `c30fcc77e5a201894fee4e23302d61d8b9f345c6` | 未包含・未採用 |
| `chappie/perf-old-compiler-control` | `001463fe7f17e725f0323e5bc4a04bbe93856084` | 未包含・未採用 |
| `chappie/perf-semantic-atom-evidence` | `c4e5638f6fd61bbf1ad3a7c7e9376fb348f8840d` | 包含済み |
| `chappie/perf-v08-hypothesis-projection` | `8677f0b10578572fa3207d0aaff84d7f83076856` | 未包含・未採用 |
| `chappie/polarity-preservation-v17` | `3e3cd271d2d62b37d7a23929e3948d47605dc19d` | 未包含・未採用 |
| `chappie/prototype-complete-baseline-20260822` | `c2d56e08f67cbc11ef98ae70f6c25af6f6e39e31` | 包含済み |
| `chappie/public-multilingual-trinity-context-20260821` | `4f1afac592e04da97cbded6a36bc6be19ddad953` | 未包含・未採用 |
| `chappie/question-scope-v19` | `ac08d837fa8105b49fd410e9abcb0c8a98afcdc7` | 未包含・未採用 |
| `chappie/relation-qualifiers-v18` | `974d87ce2c2bae67a6e30bcb5e5b93032da0cb36` | 未包含・未採用 |
| `chappie/relation-scope-v04` | `648fa4ccfc6beecfbadf4371a8d49eb9c2c2cedd` | 未包含・未採用 |
| `chappie/relative-clause-clean-v08` | `9b8ff0e95377d15f58492aa1ab2ab57eb9f5f926` | 未包含・未採用 |
| `chappie/relative-clause-coref-v08` | `7d3ee58a114260f7869bb5201413da837d1b78ca` | 未包含・未採用 |
| `chappie/repo-benchmark-runner-v0-7` | `3075f17aab0732f3d187dffa476f475399540eee` | 未包含・未採用 |
| `chappie/sanitized-scientific-capability-v1` | `bdeb9f042622f3c0330b96de3b222dc3acd43003` | 包含済み |
| `chappie/scope-aware-direct-v20` | `d7236f8e68e5f6501ff39ed6970761d3858e2147` | 包含済み |
| `chappie/scope-aware-reasoning-v05` | `86d8ab625bb2486735bf997cb840e6ac086d5ca0` | 未包含・未採用 |
| `chappie/scope-aware-retrieval-v06` | `f5de28ebdf686c5e2c0e75a28a19c1351c18660e` | 未包含・未採用 |
| `chappie/search-focus-clean-v13` | `30879fe41d015008a521574bd524966af0595161` | 未包含・未採用 |
| `chappie/structured-kernel-v16` | `8d80af1ce5fa6da0fab3387f6bcd2a932fafd869` | 未包含・未採用 |
| `rebuild/hds-judgement-subject-v1` | `0e2e966c1720efee25301a89e5fea8ad29dbbab5` | 包含済み |
| `redo/hds-existing-minidora-integration` | `9265cb94032afc4688b083479ca9a1c073dc3810` | 包含済み |
| `sandbox/causal-arithmetic-v1` | `a43afc468ed8142bf96ebdaf0ec117a948d13102` | 未包含・未採用 |
| `unused-validation-branch-do-not-create` | `dbecc99fd1a4d4b488e16e76014c597e2ebd50ef` | 包含済み |
