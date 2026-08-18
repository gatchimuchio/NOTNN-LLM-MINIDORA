from minidora.documents import extract, ingest
from minidora.runtime import DecisionStatus, MiniDoraEngine


def test_markdown_ingest(tmp_path):
    runtime = MiniDoraEngine(tmp_path / "docs.sqlite3")
    path = tmp_path / "規程.md"
    path.write_text("# 規程\n設備Aの停止手順は遮断、確認、記録です。", encoding="utf-8")
    assert len(ingest(runtime, path)) == 1
    result = runtime.query("設備Aの停止手順について教えてください")
    assert result.status == DecisionStatus.PASS
    assert "遮断" in result.text


def test_html_strips_script(tmp_path):
    path = tmp_path / "x.html"
    path.write_text("<h1>仕様</h1><script>秘密</script><p>安全規則</p>", encoding="utf-8")
    value = extract(path)
    assert "安全規則" in value.body
    assert "秘密" not in value.body


def test_symlink_rejected(tmp_path):
    target = tmp_path / "a.txt"
    target.write_text("x", encoding="utf-8")
    link = tmp_path / "link.txt"
    link.symlink_to(target)
    try:
        extract(link)
    except ValueError as exc:
        assert "symlink" in str(exc)
    else:
        raise AssertionError("symlinkが受理された")
