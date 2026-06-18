#!/usr/bin/env python3
"""
attendance_summary.py
=====================

Combine a year's worth of per-seminar scan files into one attendance summary.

It reads every .tsv / .csv file in a folder (one or more files per seminar,
from different organizers), works out who was present at each seminar, matches
tokens to names using your master roster, and writes two output files:

  attendance_matrix.tsv   one row per person, one column per seminar (1 = present,
                          0 = absent), plus a sessions_attended total.
  attendance_summary.tsv  one row per person: sessions attended, out of how many
                          seminars were held, and an attendance rate.

Key behaviour
-------------
* Presence is counted ONCE per (seminar, person). If two organizers both scanned
  the same person at the same seminar, that is still one attendance, not two.
* A seminar is identified by the "session" label in the files. Make sure every
  organizer types the SAME session label for a given seminar.
* Names come from the master roster (token -> name). The per-seminar files can be
  token-only; that keeps attendee names off the organizers' devices.

Usage
-----
  python3 attendance_summary.py /path/to/folder --roster /path/to/master_roster.tsv
  python3 attendance_summary.py /path/to/folder            # no roster: tokens only

Only the Python standard library is used. Nothing leaves your machine.
"""

import argparse
import csv
import os
import sys
from pathlib import Path

OUTPUT_NAMES = {"attendance_matrix.tsv", "attendance_summary.tsv"}


def detect_delimiter(first_line: str) -> str:
    """Pick tab unless the header clearly looks comma-separated."""
    if "\t" in first_line:
        return "\t"
    if "," in first_line:
        return ","
    return "\t"


def read_table(path: Path):
    """Yield rows as dicts keyed by lower-cased header names. Returns [] if the
    file has no recognisable header with a 'token' column."""
    try:
        text = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError) as exc:
        print(f"  ! could not read {path.name}: {exc}", file=sys.stderr)
        return []
    lines = text.splitlines()
    if not lines:
        return []
    delim = detect_delimiter(lines[0])
    reader = csv.reader(lines, delimiter=delim)
    rows = list(reader)
    if not rows:
        return []
    header = [h.strip().lower() for h in rows[0]]
    if "token" not in header:
        print(f"  ! skipping {path.name}: no 'token' column found", file=sys.stderr)
        return []
    out = []
    for raw in rows[1:]:
        if not any(cell.strip() for cell in raw):
            continue
        record = {header[i]: (raw[i] if i < len(raw) else "") for i in range(len(header))}
        out.append(record)
    return out


def load_roster(path: Path):
    """token -> name from the master roster. Tokens with no name keep ''."""
    roster = {}
    rows = read_table(path)
    for r in rows:
        tok = (r.get("token") or "").strip()
        if not tok:
            continue
        roster[tok] = (r.get("name") or "").strip()
    return roster


def is_present(record) -> bool:
    """A row counts as a presence unless it explicitly carries scans=0."""
    if "scans" in record:
        val = (record.get("scans") or "").strip()
        if val:
            try:
                return int(float(val)) > 0
            except ValueError:
                return True
    return True  # log-style rows: every row is one scan = present


def main():
    ap = argparse.ArgumentParser(description="Build a yearly attendance summary from per-seminar scan files.")
    ap.add_argument("folder", help="Folder containing the per-seminar .tsv/.csv files")
    ap.add_argument("--roster", help="Master roster file (token,name) for matching names", default=None)
    ap.add_argument("--out", help="Output folder (default: current directory)", default=".")
    args = ap.parse_args()

    folder = Path(args.folder)
    if not folder.is_dir():
        sys.exit(f"Not a folder: {folder}")
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    roster = load_roster(Path(args.roster)) if args.roster else {}
    roster_path = Path(args.roster).resolve() if args.roster else None

    # Gather input files, skipping our own outputs and the roster itself.
    files = sorted(
        p for p in folder.iterdir()
        if p.suffix.lower() in (".tsv", ".csv")
        and p.name not in OUTPUT_NAMES
        and (roster_path is None or p.resolve() != roster_path)
    )
    if not files:
        sys.exit(f"No .tsv/.csv files found in {folder}")

    # presence[token] -> set of session labels attended
    presence = {}
    # names discovered in the files themselves (fallback if no roster)
    found_names = {}
    sessions = set()
    blank_session_files = []
    total_rows = 0

    print(f"Reading {len(files)} file(s) from {folder} ...")
    for path in files:
        rows = read_table(path)
        if not rows:
            continue
        file_blank = False
        for r in rows:
            tok = (r.get("token") or "").strip()
            if not tok:
                continue
            if not is_present(r):
                continue
            session = (r.get("session") or "").strip()
            if not session:
                session = f"(no label) {path.name}"
                file_blank = True
            total_rows += 1
            sessions.add(session)
            presence.setdefault(tok, set()).add(session)
            nm = (r.get("name") or "").strip()
            if nm:
                found_names.setdefault(tok, nm)
        if file_blank:
            blank_session_files.append(path.name)

    session_list = sorted(sessions)

    # Build the full set of people: everyone in the roster, plus any scanned
    # token that is not in the roster (so nobody silently disappears).
    all_tokens = set(roster) | set(presence)

    def name_for(tok):
        return roster.get(tok) or found_names.get(tok) or ""

    unknown_tokens = sorted(t for t in presence if t not in roster) if roster else []

    # ---- write the attendance matrix ----
    matrix_path = out_dir / "attendance_matrix.tsv"
    ordered = sorted(all_tokens, key=lambda t: (name_for(t).lower(), t))
    with matrix_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["token", "name"] + session_list + ["sessions_attended"])
        for tok in ordered:
            attended = presence.get(tok, set())
            row = [tok, name_for(tok)] + [("1" if s in attended else "0") for s in session_list]
            row.append(str(len(attended)))
            w.writerow(row)

    # ---- write the per-person summary ----
    summary_path = out_dir / "attendance_summary.tsv"
    n_sessions = len(session_list)
    with summary_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(["token", "name", "sessions_attended", "sessions_held", "attendance_rate"])
        for tok in ordered:
            attended = len(presence.get(tok, set()))
            rate = f"{attended / n_sessions:.2%}" if n_sessions else "0%"
            w.writerow([tok, name_for(tok), attended, n_sessions, rate])

    # ---- console overview ----
    print(f"\nSeminars found: {n_sessions}")
    for s in session_list:
        n_here = sum(1 for t in presence if s in presence[t])
        print(f"  - {s}: {n_here} present")
    print(f"\nPeople in summary: {len(all_tokens)}")
    print(f"Total presence records counted: {total_rows}")
    print(f"\nWrote:\n  {matrix_path}\n  {summary_path}")

    if blank_session_files:
        print("\nWARNING: these files had rows with no session label "
              "(grouped per-file, which may split one seminar):")
        for n in blank_session_files:
            print(f"  - {n}")
    if unknown_tokens:
        print(f"\nNOTE: {len(unknown_tokens)} scanned token(s) were not in the master roster "
              "(no name attached):")
        for t in unknown_tokens:
            print(f"  - {t}")


if __name__ == "__main__":
    main()
