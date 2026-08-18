from minidora_k3.挙動変換 import BehaviorProbe, compile_behavior_probes


def test_挙動試験を命令雛形へ変換():
    probes = (
        BehaviorProbe("b1", "not True は", "False", "合格", "Kimi K3", "probe://b1", {}),
        BehaviorProbe("a1", "(2 + 3) =", "5", "合格", "Kimi K3", "probe://a1", {}),
    )
    rows = compile_behavior_probes(probes)
    assert {row.task_family for row in rows} == {"論理式", "算術"}
    assert all("HDS採否" in row.opcodes for row in rows)
    assert all(row.generalization_state == "反実仮想及び保留標本検証要" for row in rows)
