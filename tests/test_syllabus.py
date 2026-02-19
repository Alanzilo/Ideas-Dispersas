from pathlib import Path

from app.syllabus import parse_syllabus_csv


def test_parse_syllabus_csv(tmp_path: Path):
    csv_path = tmp_path / "temario.csv"
    csv_path.write_text("date,topic\n2026-02-19,Shock séptico\n", encoding="utf-8")
    rows = parse_syllabus_csv(csv_path)
    assert len(rows) == 1
    assert rows[0].date == "2026-02-19"
    assert rows[0].topic == "Shock séptico"
