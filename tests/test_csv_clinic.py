"""Tests for csv_clinic — inspect, clean, convert. stdlib only."""

import csv

import pytest

import csv_clinic as cc


@pytest.fixture
def rows():
    return [
        ["Roll No", "Student Name  ", "Email ", "Score "],
        ["101", "  Priya Sharma ", "priya@x.com", "88.5"],
        ["102", "Ravi Kumar", "ravi@x.com", "91"],
        [],
        ["102", "Ravi Kumar", "ravi@x.com", "91"],
    ]


def test_sniff_type_narrows():
    assert cc.sniff_type(["1", "2"]) == "int"
    assert cc.sniff_type(["1", "2.5"]) == "float"
    assert cc.sniff_type(["2024-06-01", "2024-07-11"]) == "date"
    assert cc.sniff_type(["abc", "1"]) == "text"
    assert cc.sniff_type(["", "  "]) == "empty"


def test_normalize_header():
    assert cc.normalize_header("Student Name  ") == "student_name"
    assert cc.normalize_header("Roll-No (old)") == "roll_no_old"
    assert cc.normalize_header("   ") == "col"


def test_clean_reports_changes(tmp_path, rows, capsys):
    src = tmp_path / "messy.csv"
    cc.write_rows(str(src), rows)
    dst = tmp_path / "clean.csv"
    rc = cc.cmd_clean(type("A", (), {"source": str(src), "dest": str(dst), "delimiter": ",",
                                     "keep_headers": False, "keep_empty": False,
                                     "keep_duplicates": False, "no_trim": False}))
    assert rc == 0
    out = list(csv.reader(open(dst, newline="", encoding="utf-8")))
    assert out[0] == ["roll_no", "student_name", "email", "score"]
    assert len(out) - 1 == 2                     # blank + duplicate rows gone
    assert out[1][1] == "Priya Sharma"           # trimmed
    text = capsys.readouterr().out
    assert "headers normalized" in text and "1 blank rows dropped" in text
    assert "1 duplicate rows removed" in text


def test_clean_respects_keep_flags(tmp_path, rows):
    src = tmp_path / "messy.csv"
    cc.write_rows(str(src), rows)
    dst = tmp_path / "kept.csv"
    cc.cmd_clean(type("A", (), {"source": str(src), "dest": str(dst), "delimiter": ",",
                                "keep_headers": True, "keep_empty": True,
                                "keep_duplicates": True, "no_trim": True}))
    out = list(csv.reader(open(dst, newline="", encoding="utf-8")))
    assert len(out) == 5                          # nothing dropped
    assert out[0][1] == "Student Name  "          # header untouched


def test_inspect_reports_duplicates_and_types(tmp_path, rows, capsys):
    src = tmp_path / "messy.csv"
    cc.write_rows(str(src), rows)
    cc.cmd_inspect(type("A", (), {"path": str(src)}))
    out = capsys.readouterr().out
    assert "3 data rows, 4 columns" in out        # 5 body rows minus the blank
    assert "exact duplicate rows: 1" in out
    assert "fully blank rows:     1" in out
    assert "int" in out and "float" in out


def test_convert_tsv(tmp_path, rows):
    src = tmp_path / "in.csv"
    cc.write_rows(str(src), rows[:2])
    dst = tmp_path / "out.tsv"
    cc.cmd_convert(type("A", (), {"source": str(src), "dest": str(dst), "tsv": True, "delimiter": ","}))
    text = open(dst, encoding="utf-8").read()
    assert "\t" in text and "csv" not in text.splitlines()[0]


def test_pad_ragged_rows(tmp_path):
    src = tmp_path / "ragged.csv"
    cc.write_rows(str(src), [["a", "b"], ["1"], ["2", "3"]])
    dst = tmp_path / "p.csv"
    cc.cmd_clean(type("A", (), {"source": str(src), "dest": str(dst), "delimiter": ",",
                                "keep_headers": True, "keep_empty": False,
                                "keep_duplicates": False, "no_trim": False}))
    out = list(csv.reader(open(dst, newline="", encoding="utf-8")))
    assert all(len(r) == 2 for r in out)
    assert out[1] == ["1", ""]


def test_main_dispatches(tmp_path, rows):
    src = tmp_path / "m.csv"
    cc.write_rows(str(src), rows[:2])
    assert cc.main(["inspect", str(src)]) == 0
    assert cc.main(["clean", str(src), str(tmp_path / "o.csv")]) == 0
    assert cc.main(["convert", str(src), str(tmp_path / "o.tsv"), "--tsv"]) == 0
