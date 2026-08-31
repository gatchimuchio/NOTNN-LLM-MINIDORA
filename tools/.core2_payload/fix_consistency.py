from pathlib import Path

init_path = Path('src/minidora/__init__.py')
text = init_path.read_text(encoding='utf-8')
if 'import sys\n' not in text:
    text = text.replace('from importlib import import_module\n', 'from importlib import import_module\nimport sys\n', 1)

old = '''_互換ワイルドカード = ("模型_v05",)\n\ndef __getattr__(name: str):\n    route = _公開経路.get(name)\n    if route is not None:\n        module_name, source_name = route\n        module = import_module(f".{module_name}", __name__)\n        value = getattr(module, source_name)\n        globals()[name] = value\n        return value\n    for module_name in _互換ワイルドカード:\n        module = import_module(f".{module_name}", __name__)\n        if name in getattr(module, "__all__", ()) and hasattr(module, name):\n            value = getattr(module, name)\n            globals()[name] = value\n            return value\n    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")\n'''
new = '''_互換ワイルドカード = ("模型_v05",)\n\ndef _ロード済み公開名を正規化() -> None:\n    """submodule importがpackage属性へ置いた同名moduleを公開API実体へ戻す。"""\n    for public_name, (module_name, source_name) in _公開経路.items():\n        loaded = sys.modules.get(f"{__name__}.{module_name}")\n        if loaded is None or not hasattr(loaded, source_name):\n            continue\n        current = globals().get(public_name)\n        if current is loaded or public_name not in globals():\n            globals()[public_name] = getattr(loaded, source_name)\n\ndef __getattr__(name: str):\n    route = _公開経路.get(name)\n    if route is not None:\n        module_name, source_name = route\n        module = import_module(f".{module_name}", __name__)\n        value = getattr(module, source_name)\n        globals()[name] = value\n        _ロード済み公開名を正規化()\n        return globals().get(name, value)\n    for module_name in _互換ワイルドカード:\n        module = import_module(f".{module_name}", __name__)\n        _ロード済み公開名を正規化()\n        if name in getattr(module, "__all__", ()) and hasattr(module, name):\n            value = getattr(module, name)\n            globals()[name] = value\n            return value\n    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")\n'''
if '_ロード済み公開名を正規化' not in text:
    if old not in text:
        raise RuntimeError('lazy import target block not found')
    text = text.replace(old, new, 1)
    text = text.replace(
        '''                module = import_module(f".{module_name}", __name__)\n                names.update(getattr(module, "__all__", ()))\n''',
        '''                module = import_module(f".{module_name}", __name__)\n                _ロード済み公開名を正規化()\n                names.update(getattr(module, "__all__", ()))\n''',
        1,
    )
init_path.write_text(text, encoding='utf-8')

runtime_path = Path('src/minidora/runtime.py')
text = runtime_path.read_text(encoding='utf-8')
required = '候補得点を確率へ読み替えて厳密言語模型を偽装しない。'
if required not in text:
    marker = '    旧主体主幹、Trinity記憶、K3 helperは明示接続または明示API呼出時だけ利用する。\n'
    if marker not in text:
        raise RuntimeError('runtime separation marker not found')
    text = text.replace(marker, marker + f'    {required}\n', 1)
runtime_path.write_text(text, encoding='utf-8')
