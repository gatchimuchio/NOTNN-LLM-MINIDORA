from __future__ import annotations

from threading import Barrier, get_ident
import time
import unittest

from minidora import 参照記録, 複合参照供給器


class _BarrierProvider:
    def __init__(self, name: str, ids: tuple[str, ...], barrier: Barrier, delay: float = 0.0) -> None:
        self.名称 = name
        self.ids = ids
        self.barrier = barrier
        self.delay = delay
        self.thread_id: int | None = None

    def 検索(self, 問合せ: str, 上限: int = 8):
        self.thread_id = get_ident()
        self.barrier.wait(timeout=1.0)
        if self.delay:
            time.sleep(self.delay)
        return tuple(
            参照記録(item, item, f"content:{item}", f"fixture://{item}", self.名称)
            for item in self.ids[:上限]
        )


class _FailProvider:
    名称 = "fail"

    def 検索(self, 問合せ: str, 上限: int = 8):
        raise OSError("provider down")


class 複合参照並列試験(unittest.TestCase):
    def test_Provider呼出は実際に並列で開始する(self) -> None:
        barrier = Barrier(2)
        first = _BarrierProvider("first", ("a1",), barrier, 0.02)
        second = _BarrierProvider("second", ("b1",), barrier, 0.0)
        provider = 複合参照供給器(first, second, 並列=True, 最大並列=2)

        records = provider.検索("query", 2)
        self.assertEqual([record.識別子 for record in records], ["a1", "b1"])
        self.assertIsNotNone(first.thread_id)
        self.assertIsNotNone(second.thread_id)
        self.assertNotEqual(first.thread_id, second.thread_id)

    def test_完了速度が違ってもProvider定義順round_robinを維持する(self) -> None:
        barrier = Barrier(2)
        slow = _BarrierProvider("slow", ("a1", "a2"), barrier, 0.03)
        fast = _BarrierProvider("fast", ("b1", "b2"), barrier, 0.0)
        provider = 複合参照供給器(slow, fast, 並列=True, 最大並列=2)

        records = provider.検索("query", 4)
        self.assertEqual([record.識別子 for record in records], ["a1", "b1", "a2", "b2"])

    def test_例外Providerを空poolへ閉じ他Providerを継続する(self) -> None:
        good = type(
            "GoodProvider",
            (),
            {
                "名称": "good",
                "検索": lambda self, q, limit=8: (
                    参照記録("ok", "ok", "content", "fixture://ok", "good"),
                ),
            },
        )()
        provider = 複合参照供給器(_FailProvider(), good, 並列=True)

        records = provider.検索("query", 4)
        self.assertEqual([record.識別子 for record in records], ["ok"])
        self.assertEqual(provider.最後のエラー[0][0], "fail")
        self.assertIn("provider down", provider.最後のエラー[0][1])


if __name__ == "__main__":
    unittest.main()
