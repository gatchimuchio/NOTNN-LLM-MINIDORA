from pathlib import Path

init_path = Path('src/minidora/__init__.py')
text = init_path.read_text(encoding='utf-8')
if 'import sys\n' not in text:
    text = text.replace('from importlib import import_module\n', 'from importlib import import_module\nimport sys\n', 1)

old = '''_äº’æ›ãƒ¯ã‚¤ãƒ«ãƒ‰ã‚«ãƒ¼ãƒ‰ = ("æ¨¡åž‹_v05",)\n\ndef __getattr__(name: str):\n    route = _å…¬é–‹çµŒè·¯.get(name)\n    if route is not None:\n        module_name, source_name = route\n        module = import_module(f".{module_name}", __name__)\n        value = getattr(module, source_name)\n        globals()[name] = value\n        return value\n    for module_name in _äº–æ›ãƒ¯ã‚¤ãƒ«ãƒ‰ã‚«ãƒ¼ãƒ‰:\n        module = import_module(f".{module_name}", __name__)\n        if name in getattr(module, "__all__", ()) and hasattr(module, name):\n            value = getattr(module, name)\n            globals()[name] = value\n            return value\n    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")\n'''
new = '''_äº’æ›ãƒ¯ã‚¤ãƒ«ãƒ‰ã‚«ãƒ¼ãƒ‰ = ("æ¨¡åž‹_v05",)\n\ndef _ãƒ­ãƒ¼ãƒ‰æ¸ˆã¿å…¬é–‹åã‚’æ­£è¦åŒ–() -> None:\n    """submodule importãŒpackageå±žæ€§ã¸ç½®ã„ãŸåŒåmoduleã‚’å…¬é–‹APIå®Ÿä½“ã¸æˆ»ã™ã€‚"""\n    for public_name, (module_name, source_name) in _å…¬é–‹çµŒè·¯.items():\n        loaded = sys.modules.get(f"{__name__}.{module_name}")\n        if loaded is None or not hasattr(loaded, source_name):\n            continue\n        current = globals().get(public_name)\n        if current is loaded or public_name not in globals():\n            globals()[public_name] = getattr(loaded, source_name)\n\ndef __getattr__(name: str):\n    route = _å…¬é–‹çµŒè·¯.get(name)\n    if route is not None:\n        module_name, source_name = route\n        module = import_module(f".{module_name}", __name__)\n        value = getattr(module, source_name)\n        globals()[name] = value\n        _ãƒ­ãƒ¼ãƒ‰æ¸ˆã¿å…¬é–‹åã‚’æ­£è¦åŒ–()\n        return globals().get(name, value)\n    for module_name in _äº–æ›ãƒ¯ã‚¤ãƒ«ãƒ‰ã‚«ãƒ¼ãƒ‰:\n        module = import_module(f".{module_name}", __name__)\n        _ãƒ­ãƒ¼ãƒ‰æ¸ˆã¿å…¬é–‹åã‚’æ­£è¦åŒ–()\n        if name in getattr(module, "__all__", ()) and hasattr(module, name):\n            value = getattr(module, name)\n            globals()[name] = value\n            return value\n    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")\n'''
if 'Xàëxàï8àây®"8ànXZÎ™h¾YÞ8).jÚ>Šh–2Xœ¹½Ð¥¸Ñ•áÐè(€€€¥˜½±¹½Ð¥¸Ñ•áÐè(€€€€€€€É…¥Í”IÕ¹Ñ¥µ•ÉÉ½È ±…éä¥µÁ½ÉÐÑ…É•Ð‰±½¬¹½Ð™½Õ¹œ¤(€€€Ñ•áÐ€ôÑ•áÐ¹É•Á±…”¡½±°¹•Ü°€Ä¤(€€€Ñ•áÐ€ôÑ•áÐ¹É•Á±…” (€€€€€€€€œœœ€€€€€€€€€€€€€€€µ½‘Õ±”€ô¥µÁ½ÉÑ}µ½‘Õ±”¡˜ˆ¹íµ½‘Õ±•}¹…µ•ôˆ°}}¹…µ•}|¥q¸€€€€€€€€€€€€€€€¹…µ•Ì¹ÕÁ‘…Ñ”¡•Ñ…ÑÑÈ¡µ½‘Õ±”°€‰}}…±±}|ˆ°€ ¤¤¥q¸œœœ°(€€€€€€€€œœœ€€€€€€€€€€€€€€€µ½‘Õ±”€ô¥µÁ½ÉÑ}µ½‘Õ±”¡˜ˆ¹íµ½‘Õ±•}¹…µ•ôˆ°}}¹…µ•}|¥q¸€€€€€€€€€€€€€€€sƒ­ãƒ¼ãƒ‰æ¸ˆã½ak:e¢YÞ8).jÚ"š5Œ–()\n                names.update(getattr(module, "__all__", ()))\n''',
        1,
    )
init_path.write_text(text, encoding='utf-8')

runtime_path = Path('src/minidora/runtime.py')
text = runtime_path.read_text(encoding='utf-8')
required = 'å€™è£œå¾—ç‚¹ã‚’ç¢ºçŽ‡ã¸èª­ã¹¦î8Ž8nXë>ZønŠˆŠ©îjŠYè¾8).XÞŠ8^8~8®8N8"p¦–b&WV—&VBæ÷B–âFW‡C ¢Ö&¶W"Òriz~K‹¾KÙ>K‹¾[›ž8G&–æ—GžŠ‰Žhkn8³2†VÇW.8þiˆîzK®hê^{i®8ŽŽ¿šb;ž’éA'–Fó–ëšfŽƒŽG–"§žR£ŽgŽ
/Ž	q¸œ(€€€¥˜µ…É­•È¹½Ð¥¸Ñ•áÐè(€€€€€€€É…¥Í”IÕ¹Ñ¥µ•ÉÉ½È ÉÕ¹Ñ¥µ”Í•Á…É…Ñ¥½¸µ…É­•È¹½Ð™½Õ¹œ¤(€€€Ñ•áÐ€ôÑ•áÐ¹É•Á±…”¡µ…É­•È°µ…É­•È€¬˜œ€€€íÉ•ÅÕ¥É•‘õq¸œ°€Ä¤((€€€½±‘}¡½¥•}…Ñ”€ô€œœœ€€€€€€€‘•¥Í¥½¸°ÍÕ‰©•Ð€ôÍ•±˜¹’âï’öO–B#š"@¡‰…Í”°ÍÑ…Ñ”°ƒ¢ššÆ	|¥q¸€€€€€€€¥˜Í•±˜»’âä½‘..[›’—2æ÷BæöæRæBŠhk%òîK‹¾KÙ>i[N[~[ø^š‚æBFV6—6–öâîx«nhX’–â¾ZéþŠÎx«nhX²îkùÞyY‚ÂZKiYwÓ¥ÆâfÇVRÒæöæS²7FFU².{YiéÂ%ÒÒæöæUÆârrp¢æWuö6†ö–6UövFRÒrrrFV6—6–öâÂ7V&¦V7BÒ6VÆbåþK‹¾KÙ>YŽh‰†&6RÂ7FFRÂŠhk%ò•Æâ–bFV6—6–öâîx«nhX²–â¾Zé¢†3ž*Ûš,»’Ýç•™, å¤±æ™—}:\n            value = None\n            state["çµæžœ"] = None\n'''
    if old_choice_gate in text:
        text = text.replace(old_choice_gate, new_choice_gate, 1)

    old_generic_gate = '''        decision, subject = self.Y..ù/dùd"9ˆ$
˜\ÙKÛÛ^¹â­¹¡bÈ:) y¬`—ÊWˆYˆÙ[‹¹..KÙâå¹¹ is not None and è¦æ±‚_.ä¸»ä½“æ•´å°‡å¿…é ˆ and decision.çŠ¶æ…‰ in {å®Ÿè¡ŒçŠ¶æ…‹.æ§yåf9i,y¥eßN—ˆ˜[YHH›Û™Wˆ™\Ý[H9íd9§¥Ë˜[YKXÝ
ÛÛ^¹â­¹¡bÊK™Y™\™[˜Ù\Ë\JÛÛ^¹l`¹«lŠKXÚ\Ú[Û‹Ù[‹¹..ù/dùâ­¹¡bÈÝXš™XÝ\JÙ]]ŠÙ[‹¹..ù/dù..ùnnK¹liy«mùbR"Â‚’’’ÂÆåöæÖRÂ†G5ö—"•Æârrp¢æWuövVæW&–5övFRÒrrrFV6—6–öâÂ7V&¦V7BÒ6VÆbåþK‹¾KÙ>YŽh‰†&6RÂ6öçFW‡Bîx«nhX²ÂŠhk%ò•Æâ7FFRÒF–7B†6öçFW‡Bîx«nhX²•Æâ–bFV6—6–öâîx«nhX’–â¾ZéþŠÎx«nhX²îjwžV`°ƒ–’ÇšV]ôéq¸€€€€€€€€€€€Ù…±Õ”€ô9½¹•q¸€€€€€€€€€€€ÍÑ…Ñ•l‹žÖCšzp‰t€ô9½¹•q¸€€€€€€€É•ÍÕ±Ð€ôƒžÖCšz\°Ù…±Õ”°ÍÑ…Ñ”°É•™•É•¹•Ì°ÑÕÁ±”¡½¹Ñ•áÐ»–Æš¶È¤°‘•¥Í¥½¸°Í•±˜»’âï’öOž*Ûš,€°ÍÕ‰©•Ð°ÑÕÁ±”¡•Ñ…ÑÑÈ¡Í•±˜»’âï’öO’âï–æä°€‹–Æ—š¶ß–%", ())), plan_name, hds_ir)\n'''
    if old_generic_gate in text:
        text = text.replace(old_generic_gate, new_generic_gate, 1)
runtime_path.write_text(text, encoding='utf-8')

# native v0.5å„z,®ùã¡xàjú,«9.îøàc9éîøàhøàgøàgøà xà y¥éÜ[[YWÝŒøà¤œ]Ú8àfxà¢[^jÛN88n8+ž88Ž8).K¸¾h‹N'°è¡Œè²­.î8:.8+Ž8:^8;Î8:ŽãšnÓšZÃŽf»Ž
/Ž	Ñ•ÍÑ}Á…Ñ €ôA…Ñ  Ñ•ÍÑÌ½Ñ•ÍÑ}ÉÕ¹Ñ¥µ•}É•™•É•¹•}ÁÉ½©•Ñ¥½¹}ØÄÔ¹Áäœ¤)Ñ•áÐ€ôÑ•ÍÑ}Á…Ñ ¹É•…‘}Ñ•áÐ¡•¹½‘¥¹œôÕÑ˜´àœ¤)Ñ•áÐ€ôÑ•áÐ¹É•Á±…” (€€€€œœœ€€€€€€€€ŒØÀ¸ÓŽ»Žcƒ‹ãƒ‰ãƒ©ã¨àêLŒú`bùå*9åc9åc8à¤¹.d¹£æùí¦ù¢k¸àfxà(¸à ·ˆÈ9cà¹áiù.¢9ë¥ùd!ù©'9í(¸àj8Þ8îÆVv7’ÖöGVÆ^8ævÆö&Î8).XžŸŽgŽ
/ŽŽ
Žq¸€€€€€€€€ŒÝÉ…ÁÁ•ËŽ“¯ãªãk§™©’´¸º+i¹.îh˜iÈžZÖÆÖöGVÆ^8)'F6Ž8ž8(¾8%ÆârrÀ¢rrr2bãã^8î˜	®[‹ŽZé¢†3¢®3’âï’æŽ½¹…Ñ¥Ù”ÉÕ¹Ñ¥µ—Ž3š&šr'ŽgŽ
#Ž‚ã€‚ã™ã‚ˆàï8àê8îKˆîy[¾8ŽhkN8Î›–>Ã¨æ‰€æœ‰å­lmoduleã‚’patchã™ã‚‹ã€‚\n'',
)
text = text.replace('patch("minidora.runtime_v03.HDSå€¹áiù.¢9ë¥ú`n9¢§ˆ‰Ë	Ü]Ú
›Z[šYÜ˜Kœ[[YK’ùcà¹áiù.¢9ë¥ùd!ù©'9í(¸à ‰ÊB^H^œ™\XÙJ	Ü]Ú
›Z[šYÜ˜Kœ[[YWÝŒË’ù`.xZ~jIÎ{J""rÂwF6‚‚&Ö–æ–F÷&ç'VçF–ÖRä„E>Xø.xZ~jIÎ{J.8"r§FW7E÷F‚çw&—FU÷FW‡B‡FW‡BÂVæ6öF–æsÒwWFbÓ‚r