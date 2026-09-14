"""会話実行監督の公開入口。既存v0.2へ実行Transaction v1を重ねる。"""
from .会話実行監督_基底 import 失敗署名, 監督結果, 会話実行監督版
from .会話実行監督_取引 import 会話実行監督

会話実行Transaction監督版 = 'MINIDORA-会話実行監督-Transaction-v0.1'

__all__ = ('失敗署名', '監督結果', '会話実行監督', '会話実行監督版', '会話実行Transaction監督版')
