from pathlib import Path

init_path = Path('src/minidora/__init__.py')
text = init_path.read_text(encoding='utf-8')
if 'import sys\n' not in text:
    text = text.replace('from importlib import import_module\n', 'from importlib import import_module\nimport sys\n', 1)

old = '''_互換ワイルドカード = ("模型_v05",)

def __getattr__(name: str):
    route = _公開経路.get(name)
    if route is not None:
        module_name, source_name = route
        module = import_module(f".{module_name}", __name__)
        value = getattr(module, source_name)
        globals()[name] = value
        return value
    for module_name in _互換ワイルドカード:
        module = import_module(f".{module_name}", __name__)
        if name in getattr(module, "__all__", ()) and hasattr(module, name):
            value = getattr(module, name)
            globals()[name] = value
            return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
'''
new = '''_互換ワイルドカード = ("模型_v05",)

def _ロード済み公開名を正規化() -> None:
    """submodule importがpackage属性へ置いた同名moduleを公開API実体へ戻す。"""
    for public_name, (module_name, source_name) in _公開経路.items():
        loaded = sys.modules.get(f"{__name__}.{module_name}")
        if loaded is None or not hasattr(loaded, source_name):
            continue
        current = globals().get(public_name)
        if current is loaded or public_name not in globals():
            globals()[public_name] = getattr(loaded, source_name)

def __getattr__(name: str):
    route = _公開経路.get(name)
    if route is not None:
        module_name, source_name = route
        module = import_module(f".{module_name}", __name__)
        value = getattr(module, source_name)
        globals()[name] = value
        _ロード済み公開名を正規化()
        return globals().get(name, value)
    for module_name in _互換ワイルドカード:
        module = import_module(f".{module_name}", __name__)
        _ロード済み公開名を正規化()
        if name in getattr(module, "__all__", ()) and hasattr(module, name):
            value = getattr(module, name)
            globals()[name] = value
            return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
'''
if '_ロード済み公開名を正規化' not in text:
    if old not in text:
        raise RuntimeError('lazy import target block not found')
    text = text.replace(old, new, 1)
    text = text.replace(
        '''                module = import_module(f".{module_name}", __name__)
                names.update(getattr(module, "__all__", ()))
''',
        '''                module = import_module(f".{module_name}", __name__)
                _ロード済み公開名を正規化()
                names.update(getattr(module, "__all__", ()))
''',
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

old_choice_gate = '''        decision, subject = self._主体合成(base, state, 要求_)
        if self.主体主幹 is not None and 要求_.主体整合必須 and decision.状態 in {実行状態.保留, 実行状態.失敗}:
            value = None; state["結果"] = None
'''
new_choice_gate = '''        decision, subject = self._主体合成(base, state, 要求_)
        if decision.状態 in {実行状態.保留, 実行状態.失敗}:
            value = None
            state["結果"] = None
'''
if old_choice_gate in text:
    text = text.replace(old_choice_gate, new_choice_gate, 1)

old_generic_gate = '''        decision, subject = self._主体合成(base, context.状態, 要求_)
        if self.主体主幹 is not None and 要求_.主体整合必須 and decision.状態 in {実行状態.保留, 実行状態.失敗}:
            value = None
        result = 結果(value, dict(context.状態), references, tuple(context.履歴), decision, self.主体状態, subject, tuple(getattr(self.主体主幹, "履歴", ())), plan_name, hds_ir)
'''
new_generic_gate = '''        decision, subject = self._主体合成(base, context.状態, 要求_)
        state = dict(context.状態)
        if decision.状態 in {実行状態.保留, 実行状態.失敗}:
            value = None
            state["結果"] = None
        result = 結果(value, state, references, tuple(context.履歴), decision, self.主体状態, subject, tuple(getattr(self.主体主幹, "履歴", ())), plan_name, hds_ir)
'''
if old_generic_gate in text:
    text = text.replace(old_generic_gate, new_generic_gate, 1)
runtime_path.write_text(text, encoding='utf-8')

# native v0.5へ責任が移ったため、旧runtime_v03をpatchする履歴テストを現行責任moduleへ更新する。
test_path = Path('tests/test_runtime_reference_projection_v15.py')
text = test_path.read_text(encoding='utf-8')
text = text.replace(
    '''        # v0.4のミニドラはv0.3運用経路を互換継承する。
        # 参照予算/検索はそのlegacy moduleのglobalを参照するため、
        # wrapperではなく実際の責任所有moduleをpatchする。
''',
    '''        # v0.5の通常実行責任はnative runtimeが所有する。
        # 旧runtime_v03ではなく現行責任moduleをpatchする。
''',
)
text = text.replace('patch("minidora.runtime_v03.HDS参照予算選択"', 'patch("minidora.runtime.HDS参照予算選択"')
text = text.replace('patch("minidora.runtime_v03.HDS参照検索"', 'patch("minidora.runtime.HDS参照検索"')
test_path.write_text(text, encoding='utf-8')
