# HDS監査

## Native / Projection境界
PASS。Llama 3の「自己」を内在実体へ昇格せず、観測される自己一貫性をTarget Projectionとして扱った。

## Observation / Claim分離
PASS。公開コード・Meta一次説明をOBSERVED、因果接続をMECHANISM_CANDIDATE / PRINCIPLE_CANDIDATEへ分離した。

## Residual保持
PASS。Dense因果、post-training交絡、history交絡、weight未観測、観測者Projection、K3 shared pathを未解残差として保持した。

## Legacy Projection
PASS。旧Llama3 HDS v1.0を削除・訂正せず、差分監査対象として保持する。

## K3優先順位
PASS。K3を主基盤、Llama3を自己一貫性の対抗基準、他LLMを差分観測点として扱う。

## 暫定性
PASS。最終断定ではなく、ミニドラ設計目的に対する `SCOPED_PRINCIPLE_CANDIDATE` として閉じる。

## 次の最大情報利得
1. Llama3 Base vs Instruct の長期主体一貫性比較
2. Llama3の履歴保持/除去/要約摂動
3. K3 shared path vs routed path の主体一貫性寄与分離
4. ミニドラ主体主幹のablation
