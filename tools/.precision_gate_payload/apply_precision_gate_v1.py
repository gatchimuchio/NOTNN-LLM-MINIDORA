from __future__ import annotations

from pathlib import Path

TARGET = Path('src/minidora/hds_model_projection.py')
TEST = Path('tests/test_å‚ç…§ç¢ºå®šå“è³ª.py')
DOC = Path('docs/PRECISION_GATE_V1_2026-09-01.md')

text = TARGET.read_text(encoding='utf-8')
if 'class å‚ç…§ç¢ºå®šå“è³ª:' in text:
    raise RuntimeError('precision gate already applied')

start = text.index('def _èƒ½åŠ›æ ¸çµ‚ç«¯(')
end = text.index('\ndef HDSMINIDORAæ¨¡å‹è©•ä¾¡(', start)
new_block = r'''@dataclass(frozen=True, slots=True)
class å‚ç…§ç¢ºå®šå“è³ª:
    é–‰åŒ…: bool
    ç†ç”±: str
    æ§‹é€ æ”¯æŒå‡ºå…¸: tuple[str, ...] = ()
    æ§‹é€ åè¨¼å‡ºå…¸: tuple[str, ...] = ()
    å†ç…§åˆæ”¯æŒå‡ºå…¸: tuple[str, ...] = ()
    åè»¢é›†ç´„ã®ã¿: bool = False


def _å‚ç…§ä¿¡é ¼è¾æ›¸(
    å‚ç…§è­˜åˆ¥å­: Sequence[str] | None,
    å‚ç…§ä¿¡é ¼: Sequence[float] | None,
) -> dict[str, float]:
    ids = tuple(å‚ç…§è­˜åˆ¥å­ or ())
    if å‚ç…§ä¿¡é ¼ is None:
        return {str(item): 1.0 for item in ids}
    confidence = tuple(å‚ç…§ä¿¡é ¼)
    if len(ids) != len(confidence):
        raise ValueError("å‚ç…§è­˜åˆ¥å­ã¨å‚ç…§ä¿¡é ¼ã¯åŒæ•°ã§ã‚ã‚‹å¿…è¦ãŒã‚ã‚‹")
    return {
        str(ref_id): max(0.0, float(value))
        for ref_id, value in zip(ids, confidence)
    }


def å‚ç…§ç¢ºå®šå“è³ªåˆ¤å®š(
    result: æ¨¡å‹çµæœ,
    *,
    å‚ç…§è­˜åˆ¥å­: Sequence[str] | None = None,
    å‚ç…§ä¿¡é ¼: Sequence[float] | None = None,
) -> å‚ç…§ç¢ºå®šå“è³ª:
    """ä¸€æ„ãªå‚ç…§å·®ã¨ã€å›ç­”ã‚’ç¢ºå®šã§ãã‚‹è¨¼æ‹ é–‰åŒ…ã‚’åˆ†é›¢ã™ã‚‹ã€‚"""
    answer = result.å‚ç…§æœ€æœ‰åŠ›å€™è£œID
    if answer is None:
        return å‚ç…§ç¢ºå®šå“è³ª(False, "NO_UNIQUE_REFERENCE_WINNER")

    row = next((item for item in result.å€™è£œå·® if item.å€™è£œID == answer), None)
    if row is None:
        return å‚ç…§ç¢ºå®šå“è³ª(False, "WINNER_NOT_FOUND")

    confidence = _å‚ç…§ä¿¡é ¼è¾æ›¸(å‚ç…§è­˜åˆ¥å­, å‚ç…§ä¿¡é ¼)
    reverse = any(
        str(item).casefold() == "é¸æŠæ„å›³=åè»¢"
        for item in result.æ–‡è„ˆ.æ¡ä»¶
    )

    structural_support: set[str] = set()
    structural_against: set[str] = set()
    recheck_support: set[str] = set()
    reverse_aggregate_only = False

    for contribution in row.å¯„ä¸:
        if not contribution.é–¢ä¿‚å.startswith(
            ("å‚ç…§é–¢ä¿‚å¯„ä¸", "å€™è£œå…±åŒå‚ç…§", "å€™è£œå…±åŒå†ç…§åˆ")
        ):
            continue
        for raw in contribution.æ ¹æ‹ :
            marker = str(raw)
            if marker.startswith("å‚ç…§:"):
                parts = marker.split(":")
                if len(parts) < 3:
                    continue
                ref_id = ":".join(parts[1:-1])
                try:
                    delta = int(parts[-1])
                except ValueError:
                    continue
                if confidence.get(ref_id, 1.0) <= 0.0:
                    continue
                effective = -delta if reverse else delta
                if effective > 0:
                    structural_support.add(ref_id)
                elif effective < 0:
                    structural_against.add(ref_id)
                continue

            if marker.startswith("å†ç…§åˆ:"):
                parts = marker.split(":")
                if len(parts) < 4:
                    continue
                ref_id = ":".join(parts[1:-2])
                if confidence.get(ref_id, 1.0) > 0.0:
                    recheck_support.add(ref_id)
                continue

            if marker.startswith("åè»¢ä¾‹å¤–:"):
                reverse_aggregate_only = True

    if structural_support and structural_against:
        return å‚ç…§ç¢ºå®šå“è³ª(
            False,
            "STRUCTURAL_EVIDENCE_CONFLICT",
            tuple(sorted(structural_support)),
            tuple(sorted(structural_against)),
            tuple(sorted(recheck_support)),
            reverse_aggregate_only,
        )
    if structural_support:
        return å‚ç…§ç¢ºå®šå“è³ª(
            True,
            "STRUCTURAL_EVIDENCE_CLOSED",
            tuple(sorted(structural_support)),
            (),
            tuple(sorted(recheck_support)),
            reverse_aggregate_only,
        )
    if len(recheck_support) >= 2:
        return å‚ç…§ç¢ºå®šå“è³ª(
            True,
            "MULTI_SOURCE_WEAK_EVIDENCE_CLOSED",
            (),
            (),
            tuple(sorted(recheck_support)),
            reverse_aggregate_only,
        )
    if reverse_aggregate_only:
        return å‚ç…§ç¢ºå®šå“è³ª(
            False,
            "REVERSE_AGGREGATE_UNTRACEABLE",
            (),
            (),
            tuple(sorted(recheck_support)),
            True,
        )
    if len(recheck_support) == 1:
        return å‚ç…§ç¢ºå®šå“è³ª(
            False,
            "SINGLE_WEAK_SOURCE",
            (),
            (),
            tuple(sorted(recheck_support)),
            False,
        )
    return å‚ç…§ç¢ºå®šå“è³ª(False, "REFERENCE_EVIDENCE_UNTRACEABLE")


def _èƒ½åŠ›æ ¸çµ‚ç«¯(
    result: æ¨¡å‹çµæœ,
    *,
    å‚ç…§è­˜åˆ¥å­: Sequence[str] | None = None,
    å‚ç…§ä¿¡é ¼: Sequence[float] | None = None,
) -> tuple[str, str | None, list[str]]:
    """å¾Œæ®µHDSã‚’ä½¿ã‚ãšã€èƒ½åŠ›æ ¸è‡ªèº«ã§å‚ç…§å·®ã¨è¨¼æ‹ é–‰åŒ…ã‚’åˆ†é›¢ã—ã¦é–‰ã˜ã‚‹ã€‚"""
    answer = result.å‚ç…§æœ€æœ‰åŠ›å€™è£œID
    if answer is not None:
        quality = å‚ç…§ç¢ºå®šå“è³ªåˆ¤å®š(
            result,
            å‚ç…§è­˜åˆ¥å­=å‚ç…§è­˜åˆ¥å­,
            å‚ç…§ä¿¡é ¼=å‚ç…§ä¿¡é ¼,
        )
        if not quality.é–‰åŒ…:
            return (
                "SUSPEND",
                None,
                [
                    "MINIDORA_MODEL_CORE_REFERENCE_EVIDENCE_NOT_CLOSED",
                    quality.ç†ç”±,
                ],
            )
        return (
            "APPROVE",
            answer,
            [
                "MINIDORA_MODEL_CORE_SELECTED",
                "REFERENCE_CONTRIBUTION_PRESENT",
                "REFERENCE_DIFFERENCE_SELECTED",
                quality.ç†ç”±,
            ],
        )

    ref_scores = result.å‚ç…§å€™è£œè¾æ›¸()
    if not any(ref_scores.values()):
        return (
            "SUSPEND",
            None,
            ["MINIDORA_MODEL_CORE_NO_REFERENCE_CONTRIBUTION", "NO_GUESS"],
        )
    return (
        "SUSPEND",
        None,
        [
            "MINIDORA_MODEL_CORE_NO_UNIQUE_POSITIVE_DIFFERENCE",
            "REFERENCE_DIFFFENCE_NOT_UNIQUE",
        ],
    )
'''
text = text[:start] + new_block + text[end:]

old = '''    if å‚ç…§ä¿¡é ¼ is not None and len(tuple(å‚ç…§ä¿¡é ¼)) != len(data_irs):\n        raise ValueError("å‚ç…§ä¿¡é ¼ã§Data IPã¨åŒæ•°ã§ã‚ã‚‹å¿…è¦ãŒã‚ã‚‹")\n'''new = '''    confidence_values = tuple(å‚ç…§ä¿¡é ¼) if å‚ç…§ä¿¡é ¼ is not None else None\n    if confidence_values is not None and len(confidence_values) != len(data_irs):\n        raise ValueError("å‚ç…§ä¿¡é ¼ã¯Data IRã¨åŒæ•°ã§ã‚ã‚‹å¿…è¦ãŒã‚ã‚‹"%q¸œœœ)¥˜½±¹½Ğ¥¸Ñ•áĞè(€€€É…¥Í”IÕ¹Ñ¥µ•ÉÉ½È ½¹™¥‘•¹”Ù…±¥‘…Ñ¥½¸Ñ…É•Ğ¹½Ğ™½Õ¹œ¤)Ñ•áĞ€ôÑ•áĞ¹É•Á±…”¡½±°¹•Ü°€Ä¤()½±€ô€œ€€€ÉÕ¹Ñ¥µ•}ÍÑ…Ñ”°…¹Íİ•È°É•…Í½¹Ì€ô¢÷–*oš‚ãÖ®¼¡É•ÍÕ±Ğ¥q¸œ)¹•Ü€ô€œœœ€€€ÉÕ¹Ñ¥µ•}ÍÑ…Ñ”°…¹Íİ•È°É•…Í½¹Ì€ô¢÷–*oš‚ãÖ®¼¡q¸€€€€€€€É•ÍÕ±Ğ±q¸€€€€€€€ƒ–>Ÿ¢¶c–"—–¶@õ¥‘Ì±q¸€€€€€€€ƒ–>Ÿ’ş‡¦‚ğõ½¹™¥‘•¹•}Ù…±Õ•Ì±q¸€€€€¥q¸œœœ)¥˜½±¹½Ğ¥¸Ñ•áĞè(€€€É…¥Í”IÕ¹Ñ¥µ•ÉÉ½È Ñ•Éµ¥¹…°Ñ…É•Ğ¹½Ğ™½Õ¹œ¤)Ñ•áĞ€ôÑ•áĞ¹É•Á±…”¡½±°¹•Ü°€Ä¤()½±€ô€œ€€€€‰!M5%9%=I–Â–öÇÖCšzpˆ±q¸€€€€‰!M5%9%=Iš¢‡–z/¢¦W’ú„ˆ±q¸œ)¹•Ü€ô€œ€€€€‰!M5%9%=I–Â–öÇÖCšzpˆ±q¸€€€€‹–>ŸŠë–ºk–N¢Î¨ˆ±q¸€€€€‹–>ŸŠë–ºk–N¢Î«–"“–ºhˆ±q¸€€€€‰!M5%9%=Iš¢‡–z/¢¦W’ú„ˆ±q¸œ)¥˜½±¹½Ğ¥¸Ñ•áĞè(€€€É…¥Í”IÕ¹Ñ¥µ•ÉÉ½È }}…±±}|Ñ…É•Ğ¹½Ğ™½Õ¹œ¤)Ñ•áĞ€ôÑ•áĞ¹É•Á±…”¡½±°¹•Ü°€Ä¤)QIP¹İÉ¥Ñ•}Ñ•áĞ¡Ñ•áĞ°•¹½‘¥¹œôÕÑ˜´àœ¤()QMP¹İÉ¥Ñ•}Ñ•áĞ¡Èœœ™É½´}}™ÕÑÕÉ•}|¥µÁ½ÉĞ…¹¹½Ñ…Ñ¥½¹Ì()¥µÁ½ÉĞÕ¹¥ÑÑ•ÍĞ()™É½´µ¥¹¥‘½É„¹¡‘Í}µ½‘•±}ÁÉ½©•Ñ¥½¸¥µÁ½ÉĞƒ–>ŸŠë–ºk–N¢Î«–"“–ºh)™É½´µ¥¹¥‘½É„»š¢‡–z,¥µÁ½ÉĞƒ–¦£¢¢¢ª{*Ûš,°ƒšZ¢#’îc7¢¢¢ª{*Ûš,°ƒš"C®/–Ş¸°ƒš¢‡–z/ÖCšzp°ƒ¦Z‹’ş–¾’â8(()‘•˜}É•ÍÕ±Ğ ©½¹ÑÉ¥‰ÕÑ¥½¹Ìèƒ¦Z‹’ş–¾’â8°É•Ù•ÉÍ”è‰½½°€ô…±Í”¤€´øƒš¢‡–z/ÖCšzpè(€€€¥¹Ñ•É¹…°€ôƒ–¦£¢¢¢ª{*Ûš, ˆˆ°€‹¢«Û¢¢¢ªxé©„ˆ°™É½é•¹Í•Ğ ¤¤(€€€½¹Ñ•áĞ€ôƒšZ¢#’îc7¢¢¢ª{*Ûš,¡¥¹Ñ•É¹…°°ƒšv‡’îØô ‹¦ãš*{š?–nÌ÷–>7¢îˆˆ°¤¥˜É•Ù•ÉÍ”•±Í”€ ¤¤(€€€É•ÑÕÉ¸ƒš¢‡–z/ÖCšzp (€€€€€€€½¹Ñ•áĞ°(€€€€€€€€£š"C®/–Ş¸ ‰ˆ°€Ä°ÑÕÁ±”¡½¹ÑÉ¥‰ÕÑ¥½¹Ì¤¤°ƒš"C®/–Ş¸ ‰ˆ°€À°€ ¤¤¤°(€€€€€€€€‰ˆ°€ ¤°€ ¤°ƒ–>Ÿšršr'–*o–g¢q%ô‰ˆ°(€€€€¤(()±…ÍÌƒ–>ŸŠë–ºk–N¢Î«¢¦›¦¢L¡Õ¹¥ÑÑ•ÍĞ¹Q•ÍÑ…Í”¤è(€€€‘•˜Ñ•ÍÑ–òÇ’â–ë–ãƒGŸ¿–n{¶S
K¦Z'c«¡Í•±˜¤è(€€€€€€€Ä€ôƒ–>ŸŠë–ºk–N¢Î«–"“–ºh (€€€€€€€€€€€}É•ÍÕ±Ğ£¦Z‹’ş–¾’â8 ‹–g¢s–Ç–B3–>œˆ°€Ä°€ ‹–7Ÿ–B éÈÄèÀèÄˆ°¤¤¤°(€€€€€€€€€€€ƒ–>Ÿ¢¶c–"—–¶@ô ‰ÈÄˆ°¤°ƒ–>Ÿ’ş‡¦‚ğô Ä¸À°¤°(€€€€€€€€¤(€€€€€€€Í•±˜¹…ÍÍ•ÉÑ…±Í”¡Ä»¦Z'–2¤(€€€€€€€Í•±˜¹…ÍÍ•ÉÑÅÕ…°¡Ä»BRÄ°€‰M%91}]-}M=UIˆ¤((€€€‘•˜Ñ•ÍÑ–òÇ¢¢óš.ƒ
’ê3.³®/–ë–ã«
'¦Z'–2Ÿ7
,¡Í•±˜¤è(€€€€€€€Ä€ôƒ–>ŸŠë–ºk–N¢Î«–"“–ºh (€€€€€€€€€€€}É•ÍÕ±Ğ£¦Z‹’ş–¾’â8 ‹–g¢s–Ç–B3–>œˆ°€Ä°€ ‹–7Ÿ–B éÈÄèÀèÄˆ°€‹–7Ÿ–B éÈÈèÀèÄˆ¤¤¤°(€€€€€€€€€€€ƒ–>Ÿ¢¶c–"—–¶@ô ‰ÈÄˆ°€‰ÈÈˆ¤°ƒ–>Ÿ’ş‡¦‚ğô À¸È°€À¸ä¤°(€€€€€€€€¤(€€€€€€€Í•±˜¹…ÍÍ•ÉÑQÉÕ”¡Ä»¦Z'–2¤((€€€‘•˜Ñ•ÍÑšb;’ëš/¦ƒšR¿š2¿’â.³®/–ë–ãŸ
¦Z'–2g
,¡Í•±˜¤è(€€€€€€€Ä€ôƒ–>ŸŠë–ºk–N¢Î«–"“–ºh (€€€€€€€€€€€}É•ÍÕ±Ğ£¦Z‹’ş–¾’â8 ‹–>Ÿ¦Z‹’ş–¾’â8ˆ°€È°€ ‹–>œéÈÄèÈˆ°¤¤¤°(€€€€€€€€€€€ƒ–>Ÿ¢¶c–"—–¶@ô ‰ÈÄˆ°¤°ƒ–>Ÿ’ş‡¦‚ğô À¸Ä°¤°(€€€€€€€€¤(€€€€€€€Í•±˜¹…ÍÍ•ÉÑQÉÕ”¡Ä»¦Z'–2¤(€€€€€€€Í•±˜¹…ÍÍ•ÉÑÅÕ…°¡Ä»BRÄ°€‰MQIUQUI1}Y%9}1=Mˆ¤((€€€‘•˜Ñ•ÍÑš/¦ƒšR¿š2£–>7¢¢ó¿nãšºëokVg’şwg
,¡Í•±˜¤è(€€€€€€€Ä€ôƒ–>ŸŠë–ºk–N¢Î«–"“–ºh (€€€€€€€€€€€}É•ÍÕ±Ğ£¦Z‹’ş–¾’â8 ‹–>Ÿ¦Z‹’ş–¾’â8ˆ°€Ä°€ ‹–>œéÈÄèÈˆ°€‹–>œéÈÈè´Èˆ¤¤¤°(€€€€€€€€€€€ƒ–>Ÿ¢¶c–"—–¶@ô ‰ÈÄˆ°€‰ÈÈˆ¤°ƒ–>Ÿ’ş‡¦‚ğô Ä¸À°€Ä¸À¤°(€€€€€€€€¤(€€€€€€€Í•±˜¹…ÍÍ•ÉÑ…±Í”¡Ä»¦Z'–2¤(€€€€€€€Í•±˜¹…ÍÍ•ÉÑÅÕ…°¡Ä»BRÄ°€‰MQIUQUI1}Y%9}=91%Pˆ¤((€€€‘•˜Ñ•ÍÑ–B3’â–òÇ–ë–ã»¢’¢÷¿.³®/¢¢óš.ƒ¯«
'«¡Í•±˜¤è(€€€€€€€Ä€ôƒ–>ŸŠë–ºk–N¢Î«–"“–ºh (€€€€€€€€€€€}É•ÍÕ±Ğ£¦Z‹’ş–¾’â8 ‹–g¢s–Ç–B3–>œˆ°€È°€ ‹–7Ÿ–B éÈÄèÀèÄˆ°€‹–7Ÿ–B éÈÄèÀèÄˆ¤¤¤°(€€€€€€€€€€€ƒ–>Ÿ¢¶c–"—–¶@ô ‰ÈÄˆ°¤°ƒ–>Ÿ’ş‡¦‚ğô Ä¸À°¤°(€€€€€€€€¤(€€€€€€€Í•±˜¹…ÍÍ•ÉÑ…±Í”¡Ä»¦Z'–2¤((€€€‘•˜Ñ•ÍÑ–>7¢î‹–V?¦†3Ÿ¿š/¦ƒ–Ş»»²›–>ß
K–>7¢î‹_›¢ª·
 ¡Í•±˜¤è(€€€€€€€Ä€ôƒ–>ŸŠë–ºk–N¢Î«–"“–ºh (€€€€€€€€€€€}É•ÍÕ±Ğ£¦Z‹’ş–¾’â8 ‹–>Ÿ¦Z‹’ş–¾’â8ˆ°€È°€ ‹–>œéÈÄè´Èˆ°¤¤°É•Ù•ÉÍ”õQÉÕ”¤°(€€€€€€€€€€€ƒ–>Ÿ¢¶c–"—–¶@ô ‰ÈÄˆ°¤°ƒ–>Ÿ’ş‡¦‚ğô Ä¸À°¤°(€€€€€€€€¤(€€€€€€€Í•±˜¹…ÍÍ•ÉÑQÉÕ”¡Ä»¦Z'–2¤((€€€‘•˜Ñ•ÍÑ–>7¢î‰…É•…Ñ—ƒGŸ¿–ë–ã¢ş÷¢Ş‡’â7¢÷«»Ÿ¦Z'c«¡Í•±˜¤è(€€€€€€€Ä€ôƒ–>ŸŠë–ºk–N¢Î«–"“–ºh (€€€€€€€€€€€}É•ÍÕ±Ğ£¦Z‹’ş–¾’â8 ‹–g¢s–Ç–B3–>œˆ°€Ä°€ ‹–>7¢î‹’ú/–’XèÀèÀ´øÈèÌˆ°¤¤°É•Ù•ÉÍ”õQÉÕ”¤°(€€€€€€€€€€€ƒ–>Ÿ¢¶c–"—–¶@ô ‰ÈÄˆ°¤°ƒ–>Ÿ’ş‡¦‚ğô Ä¸À°¤°(€€€€€€€€¤(€€€€€€€Í•±˜¹…ÍÍ•ÉÑ…±Í”¡Ä»¦Z'–2¤(€€€€€€€Í•±˜¹…ÍÍ•ÉÑÅÕ…°¡Ä»BRÄ°€‰IYIM}IQ}U9QI	1ˆ¤((€€€‘•˜Ñ•ÍÑ’ş‡¦‚ğÃ»–>Ÿ
K¢¢óš.ƒ¯šVÃ#«¡Í•±˜¤è(€€€€€€€Ä€ôƒ–>ŸŠë–ºk–N¢Î«–"“–ºh (€€€€€€€€€€€}É•ÍÕ±Ğ£¦Z‹’ş–¾’â8 ‹–>Ÿ¦Z‹’ş–¾’â8ˆ°€È°€ ‹–>œéÈÄèÈˆ°¤¤¤°(€€€€€€€€€€€ƒ–>Ÿ¢¶c–"—–¶@ô ‰ÈÄˆ°¤°ƒ–>Ÿ’ş‡¦‚ğô À¸À°¤°(€€€€€€€€¤(€€€€€€€Í•±˜¹…ÍÍ•ÉÑ…±Í”¡Ä»¦Z'–2¤(()¥˜}}¹…µ•}|€ôô€}}µ…¥¹}|œè(€€€Õ¹¥ÑÑ•ÍĞ¹µ…¥¸ ¤(œœœ°•¹½‘¥¹œôÕÑ˜´àœ¤()=¹İÉ¥Ñ•}Ñ•áĞ œœœŒƒ–>Ÿ¢¢óš.ƒ¦Z'–2…Ñ”ØÄƒŠP€ÈÀÈØ´Àä´ÀÄ((ŒŒƒn»j(+–n{¶SšVÃ
K–Š_
g»Ÿ¿«?–òÇš‚çš.ƒƒGŸ–n{¶S
K¦Z'c
/Ö3¢Ş¿
Kš*G–"Ûg
/((ŒŒƒ’â¢"³–&((´ƒ’âš?«–>Ÿ–Ş»£¢¢óš.ƒ¦Z'–2
K–"¦n‹g
/(´ƒšb;’ëš/¦ƒšR¿š2¿’â.³®/–ë–ãŸ
¦Z'–2–>¿¢÷(´ƒ¢ª{–ögï–7Ÿ–B#ƒG»–òÇšR¿š2¿’ê3.³®/–ë–ã’î—’â+
K¢ššÆg
/(´ƒš/¦ƒšR¿š2£š/¦ƒ–>7¢¢ó3–Ç–¶cg
/–‚Ó–B#¿nãšºëokVg’şwg
/(´ƒ–>7¢î‰…É•…Ñ—»ÿŸ–ë–ã¢ş÷¢Ş‡’â7¢÷«–‚Ó–B#¿Vg’şwg
/(´ƒ–>Ÿ’ş‡¦‚ó¼Ã’î—’â/ƒG
K‡–*ç–2[_šš?j«¦Zû–“¿ö»/«(´ƒ–B3’â–ë–ã»¢’¢÷
K.³®/¢¢óš.ƒ£_›šVÃ#«((ŒŒƒ–ŠV0()AEG–¶›¦‚c–~Å¥“…Í”¥¹‘•ã½±“š¶¢–g¢s–V?¦†3–nëšr'¢ª{¿–º¢šv‡’îÛ¯’öÿR£_«(œœœ°•¹½‘¥¹œôÕÑ˜´àœ¤(