"""人工PDFによる有限文字抽出・原本対応・拒否契約。実サイト回答品質ではない。"""
from dataclasses import replace
from hashlib import sha256
from io import BytesIO
import subprocess
import unittest
from unittest.mock import patch, MagicMock

from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
from minidora.公開PDF抽出 import PDF文字を抽出, _文字を読む
from minidora.公開本文取得 import 公開PDF本文取得器, 公開本文取得器, 本文取得失敗
from minidora.知識取得 import _本文検証


def 人工PDF(文字群=("Alpha", "Beta"), *, 暗号=False):
    writer = PdfWriter()
    for 文字 in 文字群:
        page = writer.add_blank_page(width=300, height=300)
        if 文字 is not None:
            font = DictionaryObject({NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"), NameObject("/BaseFont"): NameObject("/Helvetica")})
            page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"):
                DictionaryObject({NameObject("/F1"): writer._add_object(font)})})
            stream = DecodedStreamObject()
            stream.set_data(("BT /F1 12 Tf 10 200 Td (" + 文字 + ") Tj ET").encode("ascii"))
            page[NameObject("/Contents")] = writer._add_object(stream)
    if 暗号:
        writer.encrypt("private")
    out = BytesIO()
    writer.write(out)
    return out.getvalue()


class 公開PDF本文試験(unittest.TestCase):
    def test_子プロセスの実抽出と頁対応(self):
        text, pages = PDF文字を抽出(人工PDF())
        self.assertEqual(text, "Alpha\nBeta")
        self.assertEqual(pages, ((1, 0, 5), (2, 6, 10)))

    def test_原本指紋と頁対応を知識取得へ接続(self):
        raw = 人工PDF()
        reader = 公開PDF本文取得器(許可ホスト=("example.test",))
        url = "https://example.test/a.pdf"
        with patch.object(reader, "_一回取得", return_value=(200, {"content-type": "application/pdf"}, raw)):
            doc = reader.取得(url)
        _本文検証(doc, url)
        self.assertEqual(doc.転送SHA256, sha256(raw).hexdigest())
        self.assertEqual(doc.本文SHA256, sha256(doc.本文.encode()).hexdigest())
        self.assertEqual(doc.経路, (url,))
        for pages in ((), ((1, 0, 4), (2, 6, 10))):
            with self.subTest(pages=pages), self.assertRaises(ValueError):
                _本文検証(replace(doc, 抽出頁範囲=pages), url)

    def test_旧取得器はPDF拒否を維持(self):
        reader = 公開本文取得器()
        with patch.object(reader, "_一回取得", return_value=(200, {"content-type": "application/pdf"}, 人工PDF())):
            with self.assertRaises(本文取得失敗):
                reader.取得("https://example.test/a.pdf")

    def test_文字なし暗号不正頁過多は失敗(self):
        for raw in (人工PDF((None,)), 人工PDF(暗号=True), b"%PDF-invalid", 人工PDF(("A",) * 61)):
            with self.subTest(size=len(raw)), self.assertRaises(ValueError):
                PDF文字を抽出(raw)

    def test_原本サイズと時間上限を子起動前に拒否(self):
        with patch("minidora.公開PDF抽出.subprocess.Popen") as start:
            for raw, seconds in ((b"x", 8), (b"%PDF-" + b"x" * 2_000_000, 8), (人工PDF(), 0)):
                with self.assertRaises(ValueError):
                    PDF文字を抽出(raw, 秒上限=seconds)
            start.assert_not_called()

    def test_解析警告の部分本文を成功にしない(self):
        import logging
        from pypdf._page import PageObject
        def 不完全(page, **kwargs):
            logging.getLogger("pypdf._page").warning("artificial omitted content")
            return "partial"
        with patch.object(PageObject, "extract_text", 不完全), self.assertRaises(ValueError):
            _文字を読む(人工PDF(("A",)))

    def test_時間超過の子を終了して回収(self):
        child = MagicMock()
        child.communicate.side_effect = [subprocess.TimeoutExpired("worker", 0.01), (b"", b"")]
        with patch("minidora.公開PDF抽出.subprocess.Popen", return_value=child), self.assertRaises(subprocess.TimeoutExpired):
            PDF文字を抽出(人工PDF(), 秒上限=0.01)
        child.kill.assert_called_once()
        self.assertEqual(child.communicate.call_count, 2)

    def test_転送先と圧縮拒否を共有(self):
        reader = 公開PDF本文取得器(許可ホスト=("example.test",))
        for headers, raw in (({"location": "https://private.test/a"}, b""),
            ({"content-type": "application/pdf", "content-encoding": "gzip"}, 人工PDF())):
            with patch.object(reader, "_一回取得", return_value=(302 if "location" in headers else 200, headers, raw)):
                with self.assertRaises((ValueError, 本文取得失敗)):
                    reader.取得("https://example.test/a.pdf")
