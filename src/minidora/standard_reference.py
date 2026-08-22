from __future__ import annotations

from .europe_pmc_reference import EuropePMC参照供給器
from .http_reference import OpenAlex参照供給器, Wikipedia参照供給器
from .参照 import 参照供給器, 複合参照供給器


def 一般知識参照供給器(
    *,
    OpenAlex_API_key: str | None = None,
    EuropePMC有効: bool = True,
    EuropePMC同義語展開: bool = False,
    Wikipedia言語: tuple[str, ...] = ("en",),
    timeout: float = 12.0,
    最大本文文字数: int = 12000,
    並列: bool = True,
    最大並列: int = 4,
) -> 参照供給器:
    """MINIDORA標準一般知識Rを構成する。

    OpenAlex keyは呼出側が明示した場合だけ利用する。Europe PMCはAPI key不要の科学文献Rとして
    明示的に無効化されない限り使用し、Wikipediaは指定言語ごとに独立Providerとして追加する。
    複数Provider時は決定論的round-robin複合Rを返す。
    """
    providers: list[参照供給器] = []
    if OpenAlex_API_key is not None and str(OpenAlex_API_key).strip():
        providers.append(
            OpenAlex参照供給器(
                str(OpenAlex_API_key).strip(),
                timeout=timeout,
                最大本文文字数=最大本文文字数,
            )
        )

    if EuropePMC有効:
        providers.append(
            EuropePMC参照供給器(
                timeout=timeout,
                最大本文文字数=最大本文文字数,
                同義語展開=EuropePMC同義語展開,
            )
        )

    seen_languages: set[str] = set()
    for raw_language in Wikipedia言語:
        language = str(raw_language).strip().casefold()
        if not language or language in seen_languages:
            continue
        seen_languages.add(language)
        providers.append(
            Wikipedia参照供給器(
                言語=language,
                timeout=timeout,
                最大本文文字数=最大本文文字数,
            )
        )

    if not providers:
        raise ValueError("一般知識RにはOpenAlex・Europe PMC・WikipediaのProviderが1つ以上必要")
    if len(providers) == 1:
        return providers[0]
    return 複合参照供給器(
        *providers,
        名称="MINIDORA一般知識R",
        並列=並列,
        最大並列=最大並列,
    )


__all__ = ["一般知識参照供給器"]
