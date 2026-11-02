"""Day 6 evidence in motion: a video and a GIF for every test case of every run.

Reads the Playwright JSON results ``reports/results-<run>.json`` and, for each test:

- copies its video (``video: "on"`` in e2e/playwright.config.ts) to ``reports/videos/<run>/<TC>.webm``;
- builds ``reports/gifs/<run>/<TC>.gif`` from the screencast frames inside its ``trace.zip`` — Pillow only, no
  ffmpeg (Playwright's bundled ffmpeg encodes VP8 and nothing else);

then writes the gallery ``reports/test-media.md`` for the latest run (GIF inline, link to the video).
``scripts/test_report.py`` links both files from the evidence column of ``reports/test-report.md``.

    python scripts/test_media.py            # after: cd e2e && E2E_RUN=run1 npm run test:tc ; E2E_RUN=run2 ...
    python scripts/test_media.py run2       # one run only
"""

from __future__ import annotations

import io
import json
import re
import shutil
import sys
import zipfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports"
GALLERY = REPORTS / "test-media.md"
TC = re.compile(r"TC-\d{3}-\d{2}")
GIF_WIDTH = 720  # half the 1440 px viewport: text in the app stays readable
GIF_COLORS = 64
MIN_GAP_MS = 125  # ≤ 8 frames per second — enough for progress bars and streaming text
MAX_HOLD_MS = 2000  # the screencast only sends a frame when the page changes; long waits are shortened to 2 s
LAST_HOLD_MS = 2500  # keep the final state (what the TC asserts) on screen before the loop restarts
STATUS = {"passed": "PASS", "failed": "FAIL", "timedOut": "FAIL", "interrupted": "FAIL", "skipped": "skip"}


def recorded_by(path: str, started: str, seconds: float) -> bool:
    """The attachment still exists and was written during this test result — not overwritten by a later run that
    used the same folder (before outputDir was per run, run2 replaced the traces of run1)."""
    p = Path(path)
    if not p.is_file() or not started:
        return False
    t0 = datetime.fromisoformat(started.replace("Z", "+00:00")).timestamp()
    return t0 - 1 <= p.stat().st_mtime <= t0 + seconds + 30  # video / trace are flushed when the test closes


def load_tests(path: Path) -> list[dict]:
    """One entry per Playwright test: title, TC ids, status and attachment paths (video, trace)."""
    out: list[dict] = []

    def walk(suite: dict) -> None:
        for spec in suite.get("specs", []):
            for test in spec["tests"]:
                result = test["results"][-1] if test["results"] else {"status": "skipped", "attachments": []}
                started, seconds = result.get("startTime", ""), result.get("duration", 0) / 1000
                files = {
                    a["name"]: a["path"]
                    for a in result.get("attachments", [])
                    if a.get("path") and recorded_by(a["path"], started, seconds)
                }
                ids = TC.findall(spec["title"])
                if ids:
                    out.append({"title": spec["title"], "ids": ids, "status": result["status"], "files": files})
        for child in suite.get("suites", []):
            walk(child)

    for suite in json.loads(path.read_text(encoding="utf-8"))["suites"]:
        walk(suite)
    return out


def trace_frames(trace: Path) -> list[tuple[float, bytes]]:
    """(timestamp ms, JPEG) of every screencast frame recorded in a Playwright trace, in time order."""
    with zipfile.ZipFile(trace) as z:
        frames = []
        for name in z.namelist():
            if not name.endswith(".trace"):
                continue
            for line in z.read(name).decode("utf-8").splitlines():
                if '"screencast-frame"' in line:
                    event = json.loads(line)
                    frames.append((event["timestamp"], z.read(f"resources/{event['sha1']}")))
    return sorted(frames, key=lambda f: f[0])


def pace(stamps: list[float]) -> list[tuple[int, int]]:
    """(frame index, duration ms) to show: drops frames closer than MIN_GAP_MS, caps idle time at MAX_HOLD_MS."""
    kept: list[list[int]] = []
    for i, t in enumerate(stamps):
        if kept and t - stamps[kept[-1][0]] < MIN_GAP_MS:
            continue
        if kept:
            kept[-1][1] = int(min(t - stamps[kept[-1][0]], MAX_HOLD_MS))
        kept.append([i, LAST_HOLD_MS])
    return [(i, d) for i, d in kept]


def make_gif(trace: Path, out: Path) -> int:
    """Writes the GIF of one trace; returns the number of frames (0 = the trace has no screencast)."""
    # Pillow is a backend dev extra; imported here so the rest of the module needs only stdlib
    from PIL import Image

    frames = trace_frames(trace)
    plan = pace([t for t, _ in frames])
    if not plan:
        return 0
    images = []
    for i, _ in plan:
        img = Image.open(io.BytesIO(frames[i][1])).convert("RGB")
        img = img.resize((GIF_WIDTH, round(img.height * GIF_WIDTH / img.width)), Image.LANCZOS)
        # flat UI colours: a small palette without dithering keeps text sharp and the GIF ~3× smaller
        images.append(img.quantize(colors=GIF_COLORS, dither=Image.Dither.NONE))
    out.parent.mkdir(parents=True, exist_ok=True)
    images[0].save(out, save_all=True, append_images=images[1:], duration=[d for _, d in plan], loop=0, optimize=True)
    return len(images)


def media_name(ids: list[str]) -> str:
    """TC-201-03+TC-201-04 for a test that covers two test cases — test_report.py finds it by either id."""
    return "+".join(ids)


def build_run(run: str, tests: list[dict]) -> list[dict]:
    """Copies the videos and writes the GIFs of one run; returns the tests with their media paths."""
    for d in ("videos", "gifs"):
        shutil.rmtree(REPORTS / d / run, ignore_errors=True)  # media of a test that no longer exists must go
    for t in tests:
        name = media_name(t["ids"])
        t["video"] = t["gif"] = None
        video = Path(t["files"].get("video", ""))
        if video.is_file():
            t["video"] = REPORTS / "videos" / run / f"{name}.webm"
            t["video"].parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(video, t["video"])
        trace = Path(t["files"].get("trace", ""))
        if trace.is_file() and make_gif(trace, REPORTS / "gifs" / run / f"{name}.gif"):
            t["gif"] = REPORTS / "gifs" / run / f"{name}.gif"
    return tests


def gallery(run: str, tests: list[dict]) -> str:
    """Markdown gallery: one section per test, GIF inline (GitHub plays it), link to the full-length video."""

    def rel(p: Path) -> str:
        return p.relative_to(REPORTS).as_posix()

    lines = [
        f"# Video / GIF các test case — lượt `{run}`",
        "",
        "Sinh bởi `python scripts/test_media.py` từ `reports/results-" + run + ".json` — không sửa tay.",
        (
            f"GIF dựng từ screencast trong trace (≤ 8 khung/s, khoảng lặng > {MAX_HOLD_MS // 1000} s rút còn"
            f" {MAX_HOLD_MS // 1000} s); video `.webm` là bản đủ thời lượng. Bảng kết quả:"
            " [test-report.md](test-report.md)."
        ),
        "",
    ]
    for t in tests:
        lines += [f"## {t['title']} — {STATUS.get(t['status'], t['status'])}", ""]
        if t["gif"]:
            lines += [f"![{media_name(t['ids'])}]({rel(t['gif'])})", ""]
        links = [f"[video .webm]({rel(t['video'])})"] if t["video"] else ["_không có video (E2E_VIDEO=off?)_"]
        lines += [" · ".join(links), ""]
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    paths = sorted(REPORTS.glob("results-run*.json"))
    if argv:
        paths = [p for p in paths if p.stem.removeprefix("results-") in argv]
    if not paths:
        print("no reports/results-run*.json — run the suite first (see docs/test-plan.md §4)", file=sys.stderr)
        return 1
    built = {}
    for p in paths:
        run = p.stem.removeprefix("results-")
        built[run] = build_run(run, load_tests(p))
        n_video = sum(1 for t in built[run] if t["video"])
        n_gif = sum(1 for t in built[run] if t["gif"])
        print(f"{run}: {len(built[run])} tests, {n_video} videos, {n_gif} GIFs")
    last = max(built)
    GALLERY.write_text(gallery(last, built[last]), encoding="utf-8")
    print(f"{GALLERY.relative_to(ROOT)}: gallery of {last}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
