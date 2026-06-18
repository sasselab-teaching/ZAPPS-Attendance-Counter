# Seminar Attendance

A small, privacy-first system for taking attendance at a seminar series with QR codes.

Each student gets a personal QR code. At every seminar, organizers scan the codes with their
phones. After each session the scan file is sent to the coordinator, and at the end of the year a
single script turns the whole pile of files into an attendance summary.

**Everything runs locally.** The scanning page does all its work inside the browser — attendance
data is never uploaded anywhere. The QR codes hold only a random token (never a name or student
ID), so the link between a token and a real person exists in just one place: the coordinator's
master roster, on the coordinator's laptop.

There are three roles, and the rest of this README is organized around them:

| Role | What they do | Section |
|------|--------------|---------|
| **Organizers** | Scan students' codes at the seminar | [1. For organizers](#1-for-organizers-scanning-at-the-seminar) |
| **Students** | Receive a code and show it to be scanned | [2. For students](#2-for-students) |
| **Coordinator** | Collects the files and runs the year-end summary | [3. Year-end summary](#3-year-end-summary-coordinator) |

One-time admin (hosting the page, creating and emailing the codes) is in
[Setup](#setup-one-time-coordinator) at the bottom.

> Assumes the scanning page is already hosted and students already have their codes. If that's not
> done yet, start with [Setup](#setup-one-time-coordinator).

---

## 1. For organizers (scanning at the seminar)

You'll be given a single web address — the scanning page. Nothing to install.

1. On your phone, open the page in **Chrome or Safari** (not a private/incognito tab — private
   mode wipes the safety autosave).
2. Tap the **Scan** tab.
3. Fill in **Session label** with the exact label agreed for this seminar, e.g.
   `2026-06-18 Seminar 12`. **All organizers must type the same label for the same seminar** — this
   is how the four files get matched up later.
4. Put your name in **Organizer (you)**.
5. Leave **On scan** set to *Log token only* and **File** set to *TSV*.
6. Tap **Start camera** and allow camera access. It uses the rear camera.
7. Scan each student's code. A green tick means it was recorded. Scanning the same code twice
   within a few seconds is ignored, so you won't double-count by accident.
8. When the seminar ends, tap **Export scan log** and send the downloaded `.tsv` file to the
   coordinator.
9. **Before the next seminar:** tap **Clear all data** (or *Start fresh* on the recovery banner)
   and update the **Session label**. Your name and settings stay put.

Notes:

- *Log token only* means **no student names are stored on your phone** — you're just recording
  which codes were scanned. Names are matched later by the coordinator.
- Your scans are saved continuously inside the browser, so a crash or accidental refresh won't lose
  them — they reappear when you reopen the page.
- Optional: use your browser's **Add to Home Screen** for a full-screen, app-like launcher.

---

## 2. For students

1. You'll receive an **email with your personal QR code**. It's unique to you.
2. Bring it to **every** seminar — either on your phone screen or printed on paper.
3. At the door, show it to an organizer to be scanned. That's the whole process.

Your code contains only a random token — not your name and not your matriculation number — so it's
safe to keep on your phone or print out. If you didn't receive a code or you've lost it, contact the
coordinator for a replacement.

---

## 3. Year-end summary (coordinator)

Throughout the year, collect every `.tsv` file the organizers send you into one folder, for example
`attendance/`. Keep your **master roster** file (the `token,name` list you exported when you created
the codes) somewhere safe — it's what attaches names to the tokens.

Then run:

```bash
python3 attendance_summary.py path/to/attendance --roster path/to/master_roster.tsv
```

This writes two files into the current folder:

- **`attendance_matrix.tsv`** — one row per student, one column per seminar (`1` = present,
  `0` = absent), plus a `sessions_attended` total.
- **`attendance_summary.tsv`** — one row per student: sessions attended, seminars held, and an
  attendance rate.

Leave off `--roster` to get the same tables keyed by token only (no names).

What it handles for you:

- **Deduplication** — presence is counted once per (seminar, student), so a student scanned by two
  different organizers at the same seminar still counts as one attendance.
- **Both file shapes** — it reads the token-only scan logs and the counts-style roster exports, so
  it doesn't matter which export button an organizer used. A `scans=0` row is read as absent.
- **Nobody disappears** — students in the roster who never attended appear as a row of zeros.

It also prints checks to the screen worth a glance each year:

- a per-seminar headcount (a quick way to spot a missing organizer's file),
- a warning if any file had a **blank session label** (an organizer forgot to set it),
- a list of any **scanned tokens not in the master roster** (a stray or mistyped code).

Requirements: **Python 3**, standard library only — nothing to install, and it runs entirely on
your machine.

---

## Setup (one-time, coordinator)

### A. Host the scanning page on GitHub Pages

The camera only works over `https://`, which GitHub Pages provides for free. Because the page is
static and does all its work in the browser, **no attendance data is ever sent to GitHub** — it only
serves the empty tool.

1. Create a **public** GitHub repository (free GitHub Pages requires a public repo) and upload
   `index.html`.
2. Go to **Settings → Pages**. Under **Source** choose **Deploy from a branch**, set the branch to
   `main` and the folder to `/ (root)`, and **Save**.
3. After a few minutes your page is live at `https://<your-username>.github.io/<repo>/`. Share that
   URL with the organizers.

To update the tool later, edit or re-upload `index.html` and commit — Pages redeploys automatically.

### B. Create and distribute the codes

1. Open the hosted page (or `index.html` locally) and go to the **Roster & codes** tab.
2. Add every student — paste the full list into the bulk box, one name per line. Each student gets a
   random token and a QR code.
3. Use **Print all codes**, or the per-row **QR** button, to produce each student's code, and email
   each student their own code.
4. **Export the master roster** (`token,name`) and keep it private on your laptop. This is the only
   place names are linked to tokens — **do not commit it to the repository**, which is public.

### C. Agree a session-label format with the organizers

Pick one convention, e.g. `YYYY-MM-DD Seminar N`, and make sure every organizer uses it verbatim.
Dated labels also sort into chronological order in the summary.

---

## What's in this repo

- **`index.html`** — the scanning + code-generation web app (host this on GitHub Pages).
- **`attendance_summary.py`** — the year-end aggregator.
- **`README.md`** — this file.

Do **not** add the master roster or any per-session attendance files to the repo; it's public.

## Data & privacy at a glance

- QR codes carry an **opaque random token**, never a name or ID.
- Organizers' phones store **tokens only** (token-only scan mode).
- Student **names live solely in the coordinator's master roster**, on the coordinator's laptop.
- GitHub hosts only the **static tool**; all scanning, counting, and saving happen in the browser.
- The summary script runs **offline** with the standard library.
