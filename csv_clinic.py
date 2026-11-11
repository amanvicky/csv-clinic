#!/usr/bin/env python3
"""csv-clinic — diagnose and clean messy CSVs from the terminal.

inspect tells you what's wrong (types, blanks, duplicates, messy headers);
clean fixes the boring parts (trim, snake_case headers, empty rows, exact
duplicates) and reports every change. Zero dependencies, stdlib csv only.
"""

import argparse
import csv
import re
import sys
from datetime import datetime


def read_rows(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.reader(f))


def write_rows(path, rows, delimiter=","):
    with open(path, "w", newline="", encoding="utf-8") as f:
        csv.writer(f, delimiter=delimiter).writerows(rows)


def sniff_type(values):
    """The narrowest type every non-blank value fits, or 'empty'/'text'."""
    vals = [v for v in values if v.strip() != ""]
    if not vals:
        return "empty"
    for conv, name in ((int, "int"), (float, "float")):
        try:
            for v in vals:
                conv(v)
            return name
        except ValueError:
            pass
    for v in vals:
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            return "text"
    return "date"


def normalize_header(name):
    """'Student Name ' -> 'student_name'."""
    out = re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")
    return out or "col"


def cmd_inspect(args):
    rows = read_rows(args.path)
    if not rows:
        print("empty file")
        return 1
    header = rows[0]
    body = rows[1:]
    data = [r for r in body if any(c.strip() for c in r)]   # fully blank rows reported separately
    width = len(header)
    print(f"{len(data)} data rows, {width} columns\n")

    dupes = len(data) - len({tuple(r) for r in data})
    print(f"exact duplicate rows: {dupes}")
    blanks = len(body) - len(data)
    print(f"fully blank rows:     {blanks}\n")

    print(f"{'column':<22}{'type':<8}{'blank':>6}{'distinct':>10}  sample")
    for i in range(width):
        col = [r[i].strip() if i < len(r) else "" for r in data]
        distinct = {c for c in col if c != ""}
        kind = sniff_type(col)
        sample = ", ".join(sorted(distinct)[:3])
        sample = sample[:34] + ("…" if len(sample) > 34 else "")
        print(f"{header[i][:21]:<22}{kind:<8}{col.count(''):>6}{len(distinct):>10}  {sample}")
    return 0


def cmd_clean(args):
    rows = read_rows(args.source)
    header, body = rows[0], rows[1:]
    changes = []

    out_header = list(header)
    if not args.keep_headers:
        fixed = [normalize_header(h) for h in header]
        if fixed != header:
            changes.append(f"headers normalized ({sum(1 for a, b in zip(header, fixed) if a != b)} changed)")
        out_header = fixed

    trimmed = 0
    out_body = []
    for r in body:
        row = [c.strip() if not args.no_trim else c for c in r]
        row += [""] * (len(out_header) - len(row))   # pad ragged rows
        trimmed += sum(1 for a, b in zip(r, row) if a != b)
        out_body.append(row)
    if trimmed:
        changes.append(f"{trimmed} cells trimmed")

    before = len(out_body)
    if not args.keep_empty:
        out_body = [r for r in out_body if any(c for c in r)]
        dropped = before - len(out_body)
        if dropped:
            changes.append(f"{dropped} blank rows dropped")

    if not args.keep_duplicates:
        seen, uniq = set(), []
        for r in out_body:
            key = tuple(r)
            if key not in seen:
                seen.add(key)
                uniq.append(r)
        dups = len(out_body) - len(uniq)
        if dups:
            changes.append(f"{dups} duplicate rows removed")
        out_body = uniq

    write_rows(args.dest, [out_header] + out_body, args.delimiter)
    print(f"{args.source}: {len(body)} rows -> {args.dest}: {len(out_body)} rows")
    for c in changes or ["nothing to fix — already clean"]:
        print(f"  - {c}")
    return 0


def cmd_convert(args):
    rows = read_rows(args.source)
    delim_out = "\t" if args.tsv else args.delimiter
    write_rows(args.dest, rows, delim_out)
    print(f"{args.source}: {len(rows)} lines -> {args.dest} ({'tsv' if args.tsv else 'csv'})")
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description="diagnose and clean messy CSVs")
    sub = p.add_subparsers(dest="cmd", required=True)

    i = sub.add_parser("inspect", help="types, blanks, duplicates, samples")
    i.add_argument("path")
    i.set_defaults(func=cmd_inspect)

    c = sub.add_parser("clean", help="trim, normalize headers, drop blank rows and duplicates")
    c.add_argument("source")
    c.add_argument("dest")
    c.add_argument("--keep-headers", action="store_true", help="leave header names alone")
    c.add_argument("--keep-empty", action="store_true", help="keep fully blank rows")
    c.add_argument("--keep-duplicates", action="store_true", help="keep exact duplicate rows")
    c.add_argument("--no-trim", action="store_true", help="don't strip cell whitespace")
    c.add_argument("--delimiter", default=",")
    c.set_defaults(func=cmd_clean)

    cv = sub.add_parser("convert", help="re-emit the file (delimiter switch)")
    cv.add_argument("source")
    cv.add_argument("dest")
    cv.add_argument("--tsv", action="store_true", help="write tab-separated output")
    cv.add_argument("--delimiter", default=",")
    cv.set_defaults(func=cmd_convert)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
