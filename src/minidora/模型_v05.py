from __future__ import annotations

# v0.4の候補・関係評価実装は能力核として互換再利用する。
from .模型 import *  # noqa: F401,F403
from .模型 import __all__ as _能力模型公開名
from .言語確率法則 import *  # noqa: F401,F403
from .言語確率法則 import __all__ as _厳密LM公開名
from .規定参照 import *  # noqa: F401,F403
from .規定参照 import __all__ as _規定公開名

MINIDORA能力模型核 = MINIDORA模型核
標準能力模型核 = 標準模型核

__all__ = list(dict.fromkeys((
    *_能力模型公開名,
    *_厳密LM公開名,
    *_規定公開名,
    "MINIDORA能力模型核",
    "標準能力模型核",
)))
