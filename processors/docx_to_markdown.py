"""
Pandoc-powered DOCX -> Markdown converter (with media extraction, batch mode).

Requirements:
- Install Pandoc: https://pandoc.org/installing.html
- Ensure 'pandoc' is on PATH (or pass --pandoc-path).
"""

import argparse
import csv
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

DOCX_EXTS = {".docx", ".docm"}

FLAVOR_TO_TARGET = {
    "gfm": "gfm",
    "commonmark": "commonmark_x",
    "markdown": "markdown",
    "markdown_strict": "markdown_strict",
}

def which_pandoc(hint: Optional[str]) -> Optional[str]:
    if hint:
        p = Path(hint)
        if p.exists():
            return str(p)
    exe = "pandoc.exe" if os.name == "nt" else "pandoc"
    p = shutil.which(exe)
    return p

def discover_inputs(path: Path, recursive: bool) -> List[Path]:
    if path.is_file():
        return [path]
    files: List[Path] = []
    it = path.rglob("*") if recursive else path.glob("*")
    for p in it:
        if p.suffix.lower() in DOCX_EXTS:
            files.append(p)
    return files

def run_pandoc(pandoc: str, src: Path, dst_md: Path, media_dir: Path, target: str, wrap: str, math: str, title: Optional[str]) -> Tuple[bool, str]:
    dst_md.parent.mkdir(parents=True, exist_ok=True)
    media_dir.mkdir(parents=True, exist_ok=True)

    args = [
        pandoc,
        "-f", "docx",
        "-t", target,
        "--extract-media", str(media_dir).replace("\\", "/"),
        "--markdown-headings=atx",
        "--wrap", wrap,
        "-o", str(dst_md).replace("\\", "/"),
        str(src).replace("\\", "/"),
    ]

    math = math.lower()
    if math == "mathjax":
        args += ["--mathjax"]
    elif math == "webtex":
        args += ["--webtex"]
    elif math == "katex":
        args += ["--mathjax"]

    if title:
        args += ["-M", f"title={title}"]

    try:
        proc = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if proc.returncode == 0 and dst_md.exists():
            return True, "ok"
        else:
            return False, (proc.stderr or proc.stdout or f"pandoc exit {proc.returncode}")
    except Exception as e:
        return False, f"exception: {e}"

def target_paths(src: Path, outdir: Path, media_dir_name: Optional[str]) -> Tuple[Path, Path]:
    outdir.mkdir(parents=True, exist_ok=True)
    md_path = outdir / (src.stem + ".md")
    if media_dir_name:
        mdir = outdir / media_dir_name
    else:
        mdir = outdir / (src.stem + "_media")
    return md_path, mdir

def main():
    ap = argparse.ArgumentParser(description="Convert DOCX to Markdown using Pandoc (with media extraction).")
    ap.add_argument("input", help="DOCX file or folder containing DOCX.")
    ap.add_argument("output_md", nargs="?", help="Output .md path when input is a single file.")
    ap.add_argument("--outdir", default="", help="Output directory (for folder input). Default: ./md_out in the input folder.")
    ap.add_argument("--media-dir-name", default="", help="Force media folder name (default: <stem>_media).")
    ap.add_argument("--recursive", action="store_true", help="Recurse into subfolders when input is a folder.")
    ap.add_argument("--parallel", type=int, default=1, help="Parallel workers for folder conversion (default: 1).")
    ap.add_argument("--flavor", default="gfm", choices=list(FLAVOR_TO_TARGET.keys()), help="Markdown flavor (default: gfm).")
    ap.add_argument("--wrap", default="none", choices=["auto", "none", "preserve"], help="Markdown wrap mode (default: none).")
    ap.add_argument("--math", default="native", choices=["native", "mathjax", "webtex", "katex"], help="Math rendering hint (default: native).")
    ap.add_argument("--title", default="", help="Set title metadata for single-file conversion.")
    ap.add_argument("--pandoc-path", default="", help="Custom path to pandoc executable.")
    ap.add_argument("--log", default="", help="CSV log path (default: <outdir>/pandoc_log.csv).")
    args = ap.parse_args()

    pandoc = which_pandoc(args.pandoc_path or None)
    if not pandoc:
        print("❌ Pandoc not found. Install it and ensure 'pandoc' is on PATH, or pass --pandoc-path.", file=sys.stderr)
        sys.exit(2)

    src = Path(args.input).expanduser().resolve()
    if not src.exists():
        print(f"❌ Input not found: {src}", file=sys.stderr)
        sys.exit(2)

    target = FLAVOR_TO_TARGET[args.flavor]

    if src.is_file():
        if args.output_md:
            dst_md = Path(args.output_md).expanduser().resolve()
            outdir = dst_md.parent
        else:
            outdir = src.parent
            dst_md = outdir / (src.stem + ".md")
        media_dir_name = args.media_dir_name or (dst_md.stem + "_media")
        media_dir = outdir / media_dir_name
        ok, msg = run_pandoc(pandoc, src, dst_md, media_dir, target, args.wrap, args.math, args.title or src.stem)
        print(("✔" if ok else "✖"), src.name, "->", dst_md.name, "-", msg)
        sys.exit(0 if ok else 1)

    if args.outdir:
        outdir = Path(args.outdir).expanduser().resolve()
    else:
        outdir = src / "md_out"
    outdir.mkdir(parents=True, exist_ok=True)

    files = discover_inputs(src, recursive=args.recursive or True)
    if not files:
        print("⚠ No DOCX files found.")
        sys.exit(0)

    def convert(p: Path):
        md_path, mdir = target_paths(p, outdir, args.media_dir_name or None)
        ok, msg = run_pandoc(pandoc, p, md_path, mdir, target, args.wrap, args.math, title=p.stem)
        return p, md_path, ok, msg

    log_rows = []
    if args.parallel <= 1:
        for i, p in enumerate(files, 1):
            res_p, md_path, ok, msg = convert(p)
            print(f"[{i}/{len(files)}] {p.name} -> {md_path.name}: {'OK' if ok else 'FAIL'} ({msg})")
            log_rows.append({"src": str(p), "dst": str(md_path), "ok": ok, "msg": msg})
    else:
        with ThreadPoolExecutor(max_workers=args.parallel) as ex:
            futs = {ex.submit(convert, p): p for p in files}
            done = 0
            total = len(futs)
            for fut in as_completed(futs):
                done += 1
                p, md_path, ok, msg = fut.result()
                print(f"[{done}/{total}] {p.name} -> {md_path.name}: {'OK' if ok else 'FAIL'} ({msg})")
                log_rows.append({"src": str(p), "dst": str(md_path), "ok": ok, "msg": msg})

    log_path = Path(args.log) if args.log else (outdir / "pandoc_log.csv")
    with open(log_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["src", "dst", "ok", "msg"])
        w.writeheader()
        w.writerows(log_rows)

    success = sum(1 for r in log_rows if r["ok"])
    fail = len(log_rows) - success
    print(f"\n⏱ Done — Success: {success}, Fail: {fail}")
    print(f"🧾 Log: {log_path}")
    sys.exit(0 if fail == 0 else 1)

if __name__ == "__main__":
    main()
