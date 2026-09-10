"""人工検索結果とHTTP本文で、取得・不足再検索・来歴・制御境界を検査する。"""
from dataclasses import replace
from hashlib import sha256
import json
import unittest

from minidora.公開本文取得 import 本文を復号
from minidora.知識取得 import 知識取得器, 知識取得要求
from minidora.製品版.型 import 参照資料

BASE = "https://example.test/"


def candidate(path="a", snippet="スニペットの誤った電圧999", title="資料候補"):
    return 参照資料(path, title, "試験検索", BASE + path, 本文=snippet)


def document(path="a", text="電圧は120 V。"):
    url = BASE + path
    return 本文を復号(url, (url,), {"content-type": "text/html; charset=utf-8"},
                     f"<title>試験本文</title><p>{text}</p>".encode())


class 試験検索:
    def __init__(self, results):
        self.results, self.calls = results, []

    def 検索(self, query, limit=5):
        self.calls.append((query, limit))
        result = self.results(query) if callable(self.results) else self.results
        if isinstance(result, Exception):
            raise result
        return result


class 試験本文:
    def __init__(self, values):
        self.values, self.calls = values, []

    def 取得(self, url):
        self.calls.append(url)
        result = self.values[url]
        if isinstance(result, Exception):
            raise result
        return result


class 知識取得契約試験(unittest.TestCase):
    def setUp(self):
        self.search = 試験検索((candidate(),))
        self.fetch = 試験本文({BASE + "a": document()})
        self.runner = 知識取得器(self.search, self.fetch)
        self.request = 知識取得要求("試験機器", ("電圧",))

    def run_request(self, request=None):
        return self.runner.実行(request or self.request, 外部読取許可=True)

    def test_スニペットではなく実本文を返す(self):
        r = self.run_request()
        self.assertTrue(r.成立, r.保留理由)
        self.assertEqual(r.本文, "電圧は120 V。")
        self.assertNotIn("999", r.本文)
        self.assertEqual(r.参照[0].本文, "電圧は120 V。")
        self.assertEqual(r.データ["意味的事実検証"], "未実施")

    def test_本文摂動が後続素材に到達する(self):
        for n in (9, 222, 731, 90007):
            with self.subTest(n=n):
                self.fetch.values[BASE + "a"] = document(text=f"電圧は{n} V。")
                r = self.run_request()
                self.assertEqual(r.本文, f"電圧は{n} V。")
                self.assertEqual(r.参照[0].本文, r.本文)

    def test_必要語不在の本文をスニペットで補わない(self):
        self.fetch.values[BASE + "a"] = document(text="別の話題だけ。")
        r = self.run_request()
        self.assertFalse(r.成立)
        self.assertEqual(r.本文, "")
        self.assertEqual(r.データ["不足語"], ["電圧"])
        self.assertEqual(len(self.fetch.calls), 1)

    def test_不足語が次の検索語を変える(self):
        self.search.results = lambda q: (candidate("b"),) if "電流" in q else (candidate(),)
        self.fetch.values[BASE + "b"] = document("b", "電流は5 A。")
        r = self.run_request(replace(self.request, 必要語=("電圧", "電流")))
        self.assertTrue(r.成立, r.保留理由)
        self.assertEqual([q for q, _ in self.search.calls], ["試験機器", "試験機器 電流"])
        self.assertEqual(r.本文, "電圧は120 V。\n\n電流は5 A。")
        self.assertEqual(r.データ["不足語"], [])

    def test_必要語の変更で再検索の経路も変わる(self):
        self.search.results = lambda q: (candidate("b"),) if "電流" in q else (candidate(),)
        self.fetch.values[BASE + "b"] = document("b", "電流は5 A。")
        r = self.run_request(replace(self.request, 必要語=("電流",)))
        self.assertTrue(r.成立)
        self.assertEqual(r.本文, "電流は5 A。")
        self.assertEqual(r.データ["資料数"], 1)

    def test_不足が変わらなければ同じクエリを反復しない(self):
        self.search.results = ()
        r = self.run_request()
        self.assertFalse(r.成立)
        self.assertEqual(len(self.search.calls), 2)
        self.assertEqual(self.fetch.calls, [])

    def test_検索回数上限(self):
        r = self.run_request(replace(self.request, 必要語=("電流",), 最大検索回数=1))
        self.assertFalse(r.成立)
        self.assertEqual(len(self.search.calls), 1)

    def test_取得数上限(self):
        self.search.results = tuple(candidate(str(i)) for i in range(5))
        self.fetch.values = {BASE + str(i): document(str(i), "無関係") for i in range(5)}
        r = self.run_request(replace(self.request, 最大取得数=2, 最大資料数=2))
        self.assertFalse(r.成立)
        self.assertEqual(len(self.fetch.calls), 2)

    def test_段落を途中切断して必要語充足にしない(self):
        r = self.run_request(replace(self.request, 最大抜粋文字数=2))
        self.assertFalse(r.成立)
        self.assertEqual(r.本文, "")
        self.assertEqual(r.データ["不足語"], ["電圧"])

    def test_一致段落と原文位置の対応(self):
        self.fetch.values[BASE + "a"] = document(text="無関係な案内</p><p>電圧は120 V。</p><p>関連しない結語")
        r = self.run_request()
        self.assertTrue(r.成立)
        self.assertEqual(r.本文, "電圧は120 V。")
        for p in r.データ["抜粋"]:
            ref = next(x for x in r.参照 if x.識別子 == p["参照ID"])
            self.assertEqual(ref.本文[p["開始"]:p["終了"]], p["本文"])

    def test_取得時刻を公開時刻にしない(self):
        r = self.run_request()
        self.assertIsNone(r.参照[0].公開時刻)
        self.assertIsNone(r.データ["資料"][0]["公開時刻"])
        self.assertTrue(r.データ["資料"][0]["取得時刻"])

    def test_記録hashの再計算(self):
        r = self.run_request()
        data = dict(r.データ)
        expected = data.pop("記録SHA256")
        raw = json.dumps(data, ensure_ascii=False, sort_keys=True, allow_nan=False).encode()
        self.assertEqual(sha256(raw).hexdigest(), expected)

    def test_同じURLや同一本文で最低資料数を水増ししない(self):
        self.search.results = (candidate(), candidate("a#part"), candidate("b"))
        self.fetch.values[BASE + "b"] = document("b", "電圧は120 V。")
        r = self.run_request(replace(self.request, 最低資料数=2))
        self.assertFalse(r.成立)
        self.assertEqual(r.データ["資料数"], 1)
        self.assertEqual(self.fetch.calls.count(BASE + "a"), 1)

    def test_二資料の異なる値を勝手に一つへ確定しない(self):
        self.search.results = (candidate(), candidate("b"))
        self.fetch.values[BASE + "b"] = document("b", "電圧は240 V。")
        r = self.run_request(replace(self.request, 最低資料数=2))
        self.assertTrue(r.成立)
        self.assertIn("120", r.本文)
        self.assertIn("240", r.本文)
        self.assertEqual(len(r.参照), 2)
        self.assertEqual(r.データ["意味的事実検証"], "未実施")

    def test_明示優先ホストを先に取得する(self):
        self.search.results = (replace(candidate(), URL="https://other.test/a"), candidate("b"))
        self.fetch.values[BASE + "b"] = document("b", "電圧は240 V。")
        r = self.run_request(replace(self.request, 優先ホスト=("example.test",)))
        self.assertTrue(r.成立)
        self.assertEqual(self.fetch.calls, [BASE + "b"])
        self.assertTrue(r.データ["資料"][0]["優先元一致"])

    def test_取得故障は検索スニペットにfallbackしない(self):
        self.fetch.values[BASE + "a"] = RuntimeError("secret server text")
        r = self.run_request()
        self.assertFalse(r.成立)
        self.assertEqual(r.本文, "")
        self.assertNotIn("secret server text", str(r))
        self.assertIn("RuntimeError", str(r.データ))

    def test_検索故障を空の成功にしない(self):
        self.search.results = RuntimeError("secret")
        r = self.run_request()
        self.assertFalse(r.成立)
        self.assertNotIn("secret", str(r))
        self.assertEqual(self.fetch.calls, [])

    def test_不正URLは本文取得器へ渡さない(self):
        self.search.results = tuple(replace(candidate(), URL=u) for u in ("file:///x", "http://x.test", "https://127.0.0.1/"))
        r = self.run_request()
        self.assertFalse(r.成立)
        self.assertEqual(self.fetch.calls, [])

    def test_本文のhashまたは取得先不一致(self):
        orig = document()
        for doc in (replace(orig, 本文="改変された電圧999"), replace(orig, 要求URL=BASE + "b"),
                    replace(orig, 最終URL="http://x.test/"), replace(orig, 経路=()),
                    replace(orig, 取得時刻="2026-09-10T00:00:00")):
            with self.subTest(doc=doc):
                self.fetch.values[BASE + "a"] = doc
                self.assertFalse(self.run_request().成立)

    def test_外部読取は明示許可が必要(self):
        for value in (False, None, "true", 1):
            with self.subTest(value=value):
                self.assertFalse(self.runner.実行(self.request, 外部読取許可=value).成立)
        self.assertEqual(self.search.calls, [])

    def test_停止は検索前または取得後に観測する(self):
        r = self.runner.実行(self.request, 外部読取許可=True, 停止要求=lambda: True)
        self.assertFalse(r.成立)
        self.assertEqual(self.search.calls, [])
        r = self.runner.実行(self.request, 外部読取許可=True, 停止要求=lambda: bool(self.fetch.calls))
        self.assertFalse(r.成立)
        self.assertEqual(r.本文, "")
        self.assertEqual(r.参照, ())
        self.assertEqual(len(self.fetch.calls), 1)

    def test_停止判定故障から検索へ進まない(self):
        def fail():
            raise RuntimeError("secret")
        for callback in (fail, lambda: "false"):
            with self.subTest():
                r = self.runner.実行(self.request, 外部読取許可=True, 停止要求=callback)
                self.assertFalse(r.成立)
                self.assertNotIn("secret", str(r))
        self.assertEqual(self.search.calls, [])

    def test_不正要求で外部呼出しない(self):
        for req in (None, {}, replace(self.request, 必要語=()), replace(self.request, 必要語=["電圧"]),
                    replace(self.request, 必要語=("電圧", "電圧")), replace(self.request, 必要語=(" x",)),
                    replace(self.request, 最大検索回数=True), replace(self.request, 検索語="a\nb"),
                    replace(self.request, 最低資料数=5, 最大資料数=2),
                    replace(self.request, 優先ホスト=("example.test/path",))):
            with self.subTest(req=req):
                self.assertFalse(self.runner.実行(req, 外部読取許可=True).成立)
        self.assertEqual(self.search.calls, [])

    def test_既知の資料保存物を次runで勝手に再利用しない(self):
        a = self.run_request()
        b = self.run_request()
        self.assertTrue(a.成立 and b.成立)
        self.assertEqual(self.fetch.calls, [BASE + "a", BASE + "a"])

    def test_NFKCで語を照合しても抜粋原文は変更しない(self):
        self.fetch.values[BASE + "a"] = document(text="ＡＢＣの電圧は120。")
        r = self.run_request(replace(self.request, 必要語=("abc",)))
        self.assertTrue(r.成立)
        self.assertIn("ＡＢＣ", r.本文)

    def test_失敗部分は診断に保持するが最終本文には出さない(self):
        r = self.run_request(replace(self.request, 必要語=("電圧", "電流")))
        self.assertFalse(r.成立)
        self.assertEqual(r.本文, "")
        self.assertEqual(len(r.参照), 1)
        self.assertTrue(r.データ["抜粋"])
        self.assertEqual(r.データ["不足語"], ["電流"])


if __name__ == "__main__":
    unittest.main()
