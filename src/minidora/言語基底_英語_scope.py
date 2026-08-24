from __future__ import annotations

import re

from .言語基底_英語 import 英語関係構文


_SUBJECT = r"(?P<s>[^?!.;,\n]{1,120}?)"
_OBJECT = r"(?P<o>[^?!.;,\n]{1,120})"
_MODAL = r"(?:can|could|may|might|must|would)"
_MODAL_PASSIVE = rf"{_MODAL}\s+be"


def _modal_active(forms: str) -> re.Pattern[str]:
    return re.compile(rf"{_SUBJECT}\s+{_MODAL}\s+(?P<v>{forms})\s+{_OBJECT}", re.I)


def _modal_passive(forms: str) -> re.Pattern[str]:
    return re.compile(rf"{_SUBJECT}\s+{_MODAL_PASSIVE}\s+(?P<v>{forms})\s+by\s+{_OBJECT}", re.I)


# 様相そのものの意味（可能/必要）は英日意味scope側が同じ節から付与する。
# ここでは主語へmodalを取り込まず、関係端点と方向だけを正しく抽出する。
英語様相関係構文 = (
    英語関係構文("因果", _modal_active(r"cause|lead\s+to|result\s+in")),
    英語関係構文("因果", _modal_passive(r"caused"), True),
    英語関係構文("増加", _modal_active(r"increase|raise|enhance")),
    英語関係構文("増加", _modal_passive(r"increased|raised|enhanced"), True),
    英語関係構文("減少", _modal_active(r"decrease|reduce|lower")),
    英語関係構文("減少", _modal_passive(r"decreased|reduced|lowered"), True),
    英語関係構文("阻害", _modal_active(r"inhibit|suppress|block")),
    英語関係構文("阻害", _modal_passive(r"inhibited|suppressed|blocked"), True),
    英語関係構文("活性化", _modal_active(r"activate|stimulate")),
    英語関係構文("活性化", _modal_passive(r"activated|stimulated"), True),
    英語関係構文("生成", _modal_active(r"produce|generate")),
    英語関係構文("生成", _modal_passive(r"produced|generated"), True),
    英語関係構文("要求", _modal_active(r"require|need|depend\s+on")),
    英語関係構文("要求", _modal_passive(r"required|needed"), True),
    英語関係構文("包含", _modal_active(r"contain|include|comprise")),
    英語関係構文("使用", _modal_active(r"use|utilize|employ")),
    英語関係構文("使用", _modal_passive(r"used|utilized|employed"), True),
    英語関係構文("防止", _modal_active(r"prevent|protect\s+against|protect\s+from")),
    英語関係構文("防止", _modal_passive(r"prevented|protected"), True),
    英語関係構文("相関", _modal_active(r"associate\s+with|correlate\s+with|relate\s+to")),
)


__all__ = ["英語様相関係構文"]
