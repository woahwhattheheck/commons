from pathlib import Path
TEXT = (Path(__file__).resolve().parent / "docs/spark-mcp.md").read_text(encoding="utf-8")

def test_spark_mcp_docs_cite_wire_html():
    assert "wire.html" in TEXT
