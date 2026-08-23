from __future__ import annotations

import runpy
import sys

import minidora.hds_reference as hds_reference


_original = hds_reference._問合せ仕様


def _surface_first(ir, *, 最大候補数: int = 6):
    # 通常4択では非候補query枠は2本。現行のstructured+focusではなく、
    # v0.6実測時と同じsurface+focusを優先し、候補query数と総query予算は変えない。
    expanded = _original(ir, 最大候補数=max(int(最大候補数) + 3, 9))
    choices = [spec for spec in expanded if spec.候補 is not None]
    nonchoices = [spec for spec in expanded if spec.候補 is None]
    by_kind = {spec.種別: spec for spec in nonchoices}
    selected = []
    for kind in ("surface", "focus", "structured", "entity_relation", "entity"):
        spec = by_kind.get(kind)
        if spec is not None and all(old.問合せ.casefold() != spec.問合せ.casefold() for old in selected):
            selected.append(spec)
        if len(selected) >= max(0, int(最大候補数) - len(choices)):
            break
    return tuple((*selected, *choices))


hds_reference._問合せ仕様 = _surface_first
sys.argv = ["tools/benchmark.py", "gpqa-diamond", "--out", "gpqa_current_measurement.json"]
runpy.run_path("tools/benchmark.py", run_name="__main__")
