# -*- coding: utf-8 -*-
import os
import subprocess
from pathlib import Path
import ctypes
import stat
import csv
from datetime import datetime
import json
import tkinter as tk
from tkinter import filedialog, messagebox

APP_DIR = Path(__file__).resolve().parent
RESULT_DIR = APP_DIR / "result_AIRR_outfmat"
# Full path to reference data (can include non-ASCII).
EDIT_IMGT_REF_DIR_FULL = Path(r"C:\Users\Yohei Funakoshi\Desktop\IgBlast_refdata_edit_imgt")
LEGACY_REF_DIR_FULL = Path("C:\\Users\\Yohei Funakoshi\\Desktop\\IgBlast" + "\u7528\u53c2\u7167\u30c7\u30fc\u30bf")
DEFAULT_REF_DIR_FULL = EDIT_IMGT_REF_DIR_FULL
DEFAULT_IGBLAST = Path(r"C:\Program Files\NCBI\igblast-1.21.0\bin\igblastn.exe")
REF_DIR_FULL = DEFAULT_REF_DIR_FULL
IGBLAST = DEFAULT_IGBLAST
REF_DIR_USE = None
CONFIG_PATH = APP_DIR / "config.json"
MKLINK_WARNED = False

KERNEL32 = ctypes.windll.kernel32
KERNEL32.GetShortPathNameW.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint]
KERNEL32.GetShortPathNameW.restype = ctypes.c_uint

FILTER_OPTIONS = [
    ("No filter (original only)", None),
    ("vlen_ungapped >= 80", 80),
    ("vlen_ungapped >= 100", 100),
    ("vlen_ungapped >= 120", 120),
    ("vlen_ungapped >= 150", 150),
]
CUSTOM_REF_LABEL = "Custom (manual)"
REFDATA_PRESETS = [
    ("edit_imgt_file.pl DB (default)", EDIT_IMGT_REF_DIR_FULL),
    ("Legacy DB (python)", LEGACY_REF_DIR_FULL),
    (CUSTOM_REF_LABEL, None),
]
LAST_RUN_SUMMARY = ""
INVALID_NAME_CHARS = '<>:"/\\|?*'
MAX_PATH_LEN = 240
FILE_PREFIX_MAX = 60
THREAD_DEFAULT = ""
V_PENALTY_DEFAULT = ""
EXTEND_ALIGN5END_DEFAULT = False


def short_path(path_str):
    buf = ctypes.create_unicode_buffer(32768)
    ret = KERNEL32.GetShortPathNameW(path_str, buf, len(buf))
    return buf.value if ret else path_str


def sanitize_name(name):
    safe = "".join(
        "_" if c in INVALID_NAME_CHARS or ord(c) > 127 else c for c in name
    ).rstrip(" .")
    return safe if safe else "output"


def is_ascii_path(path_str):
    try:
        path_str.encode("ascii")
        return True
    except Exception:
        return False



def normalize_path(path_str):
    return str(path_str).rstrip("\\/").casefold()

def preset_label_for_path(path_str):
    if not path_str:
        return CUSTOM_REF_LABEL
    for label, path in REFDATA_PRESETS:
        if path and normalize_path(path_str) == normalize_path(path):
            return label
    return CUSTOM_REF_LABEL

def load_config():
    if not CONFIG_PATH.exists():
        return {}
    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as fin:
            data = json.load(fin)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_config(igblast_path, ref_dir, threads, v_penalty, extend_align5end):
    data = {
        "igblast_path": igblast_path,
        "ref_dir": ref_dir,
        "threads": threads,
        "v_penalty": v_penalty,
        "extend_align5end": extend_align5end,
    }
    with CONFIG_PATH.open("w", encoding="utf-8") as fout:
        json.dump(data, fout, ensure_ascii=False, indent=2)


def apply_config(data):
    global IGBLAST, REF_DIR_FULL, REF_DIR_USE
    igblast_path = data.get("igblast_path")
    ref_dir = data.get("ref_dir")
    if igblast_path:
        IGBLAST = Path(igblast_path)
    if ref_dir:
        ref_path = Path(ref_dir)
        if ref_path.exists():
            REF_DIR_FULL = ref_path
        else:
            REF_DIR_FULL = DEFAULT_REF_DIR_FULL
        REF_DIR_USE = None

def make_file_prefix(name, max_len):
    safe = sanitize_name(name)
    if max_len <= 0:
        return ""
    return safe[:max_len].rstrip(" .")


def make_output_dir(in_path, vlen_min, file_name, log=None):
    filter_tag = "nofilter" if vlen_min is None else f"vlen{vlen_min}"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_stem = sanitize_name(in_path.stem)

    def build_dir(stem):
        return RESULT_DIR / f"{stem}__{filter_tag}__{timestamp}"

    out_dir = build_dir(safe_stem)
    shortened = False
    if len(str(out_dir / file_name)) > MAX_PATH_LEN:
        for length in (60, 40, 20):
            stem = safe_stem[:length].rstrip(" .")
            out_dir = build_dir(stem)
            if len(str(out_dir / file_name)) <= MAX_PATH_LEN:
                shortened = True
                break
        else:
            out_dir = RESULT_DIR / f"run__{filter_tag}__{timestamp}"
            shortened = True

    base_dir = out_dir
    counter = 1
    while out_dir.exists():
        out_dir = RESULT_DIR / f"{base_dir.name}_{counter}"
        counter += 1
    if shortened and log is not None:
        log("Output folder name shortened to avoid Windows path length limits.")
    out_dir.mkdir(parents=True)
    return out_dir


def make_output_names(out_dir, stem, vlen_min, log=None):
    for length in (FILE_PREFIX_MAX, 40, 20, 10, 0):
        prefix = make_file_prefix(stem, length)
        if prefix:
            out_name = f"{prefix}.igblast.airr.tsv"
            filtered_name = f"{prefix}.igblast.airr.vlenmin{vlen_min}.tsv"
        else:
            out_name = "igblast.airr.tsv"
            filtered_name = f"igblast.airr.vlenmin{vlen_min}.tsv"
        if len(str(out_dir / out_name)) > MAX_PATH_LEN:
            continue
        if vlen_min is not None and len(str(out_dir / filtered_name)) > MAX_PATH_LEN:
            continue
        if length < FILE_PREFIX_MAX and log is not None:
            log("Output file name shortened to avoid Windows path length limits.")
        return out_name, filtered_name
    return "igblast.airr.tsv", f"igblast.airr.vlenmin{vlen_min}.tsv"


def write_summary(
    out_dir,
    in_path,
    out_path,
    vlen_min,
    igblast_path,
    ref_dir,
    threads,
    v_penalty,
    extend_align5end,
    input_records=None,
    output_rows=None,
    filtered_rows=None,
    filter_summary=None,
    filtered_path=None,
):
    lines = [
        f"Run folder: {out_dir}",
        f"Input: {in_path}",
        f"Output: {out_path}",
        f"IgBLAST: {igblast_path}",
        f"Refdata: {ref_dir}",
    ]
    if input_records is not None:
        lines.append(f"Input FASTA records: {input_records}")
    if output_rows is not None:
        lines.append(f"Output TSV rows: {output_rows}")
    if threads:
        lines.append(f"Threads: {threads}")
    else:
        lines.append("Threads: default")
    if v_penalty is None:
        lines.append("V_penalty: default")
    else:
        lines.append(f"V_penalty: {v_penalty}")
    lines.append(f"Extend_align5end: {'on' if extend_align5end else 'off'}")
    if vlen_min is None:
        lines.append("Filter: none")
    else:
        lines.append(f"Filter: vlen_ungapped >= {vlen_min}")
    if filtered_path is not None:
        lines.append(f"Filtered: {filtered_path}")
    if filtered_rows is not None:
        lines.append(f"Filtered TSV rows: {filtered_rows}")
    if filter_summary:
        lines.append(filter_summary)
    lines.append(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    text = "\n".join(lines)
    summary_path = out_dir / "summary.txt"
    summary_path.write_text(text, encoding="utf-8")
    return summary_path, text


def is_reparse_point(path):
    try:
        return bool(os.stat(path).st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)
    except Exception:
        return False


def refdata_ok(ref_dir):
    db_dir = ref_dir / "db"
    aux_file = ref_dir / "optional_file" / "human_gl.aux"
    db_bases = ("IMGT_IGHV.imgt", "IMGT_IGHD.imgt", "IMGT_IGHJ.imgt")
    for base in db_bases:
        for ext in (".nin", ".nhr", ".nsq"):
            if not (db_dir / f"{base}{ext}").exists():
                return False
    return aux_file.exists()


def get_ref_dir():
    global REF_DIR_USE, MKLINK_WARNED
    if REF_DIR_USE is not None:
        return REF_DIR_USE

    original = str(REF_DIR_FULL)
    short = short_path(original)
    ref_short = Path(short)
    if is_ascii_path(short) and refdata_ok(ref_short):
        REF_DIR_USE = ref_short
        return REF_DIR_USE

    # Create an ASCII junction under the app folder if 8.3 short path isn't available.
    junction = APP_DIR / "refdata"
    if junction.exists() and not refdata_ok(junction) and is_reparse_point(junction):
        try:
            os.rmdir(junction)
        except Exception:
            pass
    if not junction.exists():
        try:
            proc = subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(junction), str(REF_DIR_FULL)],
                capture_output=True,
                text=True,
            )
            if proc.returncode != 0 and not MKLINK_WARNED:
                details = (proc.stderr or proc.stdout or "").strip()
                msg = "Failed to create junction for reference data.\n"
                msg += "Please move the ref data to an ASCII path, or enable Developer Mode / run as admin.\n"
                if details:
                    msg += f"\nDetails:\n{details}"
                messagebox.showwarning("Reference data", msg)
                MKLINK_WARNED = True
        except Exception as exc:
            if not MKLINK_WARNED:
                messagebox.showwarning(
                    "Reference data",
                    f"Failed to create junction for reference data.\n{exc}",
                )
                MKLINK_WARNED = True
    if junction.exists() and refdata_ok(junction):
        REF_DIR_USE = junction
        return REF_DIR_USE

    REF_DIR_USE = REF_DIR_FULL
    return REF_DIR_USE


def check_prereq():
    missing = []
    if not IGBLAST.exists():
        missing.append(str(IGBLAST))
    ref_dir = get_ref_dir()
    db_dir = ref_dir / "db"
    aux_file = ref_dir / "optional_file" / "human_gl.aux"
    db_bases = ("IMGT_IGHV.imgt", "IMGT_IGHD.imgt", "IMGT_IGHJ.imgt")
    for base in db_bases:
        for ext in (".nin", ".nhr", ".nsq"):
            path = db_dir / f"{base}{ext}"
            if not path.exists():
                missing.append(str(path))
    if not aux_file.exists():
        missing.append(str(aux_file))
    if missing:
        msg = "Missing files:\n" + "\n".join(missing)
        messagebox.showerror("Missing files", msg)
        return False
    return True


def filter_airr_tsv(in_path, out_path, vlen_min, log):
    total = 0
    kept = 0
    missing = 0
    with open(in_path, "r", encoding="utf-8", errors="replace", newline="") as fin:
        reader = csv.reader(fin, delimiter="\t")
        header = next(reader, None)
        if not header:
            raise ValueError("TSV header missing.")
        try:
            v_idx = header.index("v_sequence_alignment")
        except ValueError as exc:
            raise ValueError("Missing column: v_sequence_alignment") from exc
        with open(out_path, "w", encoding="utf-8", newline="") as fout:
            writer = csv.writer(fout, delimiter="\t", lineterminator="\n")
            writer.writerow(header)
            for row in reader:
                if not row:
                    continue
                total += 1
                v_seq = row[v_idx] if v_idx < len(row) else ""
                if not v_seq or v_seq == "NA":
                    missing += 1
                    continue
                vlen = len(v_seq.replace("-", ""))
                if vlen >= vlen_min:
                    writer.writerow(row)
                    kept += 1
    summary = f"Filter vlen_ungapped >= {vlen_min}: kept {kept}/{total}, missing {missing}"
    log(summary)
    return summary


def count_fasta_records(path):
    count = 0
    with open(path, "r", encoding="utf-8", errors="replace") as fin:
        for line in fin:
            if line.startswith(">"):
                count += 1
    return count


def count_tsv_rows(path):
    count = 0
    with open(path, "r", encoding="utf-8", errors="replace") as fin:
        header = fin.readline()
        if not header:
            return 0
        for line in fin:
            if line.strip():
                count += 1
    return count


def parse_threads(text):
    value = text.strip()
    if not value:
        return None
    try:
        num = int(value)
    except ValueError as exc:
        raise ValueError("Threads must be a positive integer.") from exc
    if num <= 0:
        raise ValueError("Threads must be a positive integer.")
    return num


def parse_v_penalty(text):
    value = text.strip()
    if not value:
        return None
    try:
        num = int(value)
    except ValueError as exc:
        raise ValueError("V_penalty must be an integer (e.g., -1, -3).") from exc
    return num


def run_igblast(input_path, vlen_min, num_threads, v_penalty, extend_align5end, log):
    global LAST_RUN_SUMMARY
    LAST_RUN_SUMMARY = ""
    if not check_prereq():
        return
    if not input_path:
        messagebox.showwarning("Input", "Please select a FASTA file.")
        return
    in_path = Path(input_path)
    if not in_path.exists():
        messagebox.showerror("Input", "Input file not found.")
        return

    base_prefix = make_file_prefix(in_path.stem, FILE_PREFIX_MAX)
    base_out_name = (
        f"{base_prefix}.igblast.airr.tsv" if base_prefix else "igblast.airr.tsv"
    )
    out_dir = make_output_dir(in_path, vlen_min, base_out_name, log)
    out_name, filtered_name = make_output_names(out_dir, in_path.stem, vlen_min, log)
    out_path = out_dir / out_name

    env = os.environ.copy()
    ref_dir = get_ref_dir()
    ref_short = short_path(str(ref_dir))
    db_dir = ref_dir / "db"
    aux_file = ref_dir / "optional_file" / "human_gl.aux"
    env["IGDATA"] = ref_short

    args = [
        str(IGBLAST),
        "-query", short_path(str(in_path)),
        "-germline_db_V", short_path(str(db_dir / "IMGT_IGHV.imgt")),
        "-germline_db_D", short_path(str(db_dir / "IMGT_IGHD.imgt")),
        "-germline_db_J", short_path(str(db_dir / "IMGT_IGHJ.imgt")),
        "-auxiliary_data", short_path(str(aux_file)),
        "-domain_system", "imgt",
        "-organism", "human",
        "-ig_seqtype", "Ig",
        "-outfmt", "19",
        "-out", short_path(str(out_path)),
    ]
    if num_threads:
        args.extend(["-num_threads", str(num_threads)])
    if v_penalty is not None:
        args.extend(["-V_penalty", str(v_penalty)])
    if extend_align5end:
        args.append("-extend_align5end")

    log("Running IgBLAST...")
    try:
        proc = subprocess.run(args, env=env, capture_output=True, text=True)
    except Exception as exc:
        messagebox.showerror("Error", f"Failed to run: {exc}")
        return

    if proc.stdout:
        log(proc.stdout.strip())
    if proc.stderr:
        log(proc.stderr.strip())

    if proc.returncode == 0 and out_path.exists():
        log(f"Done: {out_path}")
        input_records = None
        output_rows = None
        try:
            input_records = count_fasta_records(in_path)
        except Exception as exc:
            log(f"Input FASTA count failed: {exc}")
        try:
            output_rows = count_tsv_rows(out_path)
        except Exception as exc:
            log(f"Output TSV count failed: {exc}")
        if vlen_min is None:
            summary_path, summary_text = write_summary(
                out_dir,
                in_path,
                out_path,
                vlen_min,
                str(IGBLAST),
                str(REF_DIR_FULL),
                num_threads,
                v_penalty,
                extend_align5end,
                input_records=input_records,
                output_rows=output_rows,
            )
            LAST_RUN_SUMMARY = summary_text
            messagebox.showinfo("Complete", f"Output:\n{out_path}\nSummary:\n{summary_path}")
            return
        filtered_path = out_dir / filtered_name
        log("Filtering TSV by vlen_ungapped...")
        try:
            summary = filter_airr_tsv(out_path, filtered_path, vlen_min, log)
        except Exception as exc:
            log(f"Filter error: {exc}")
            messagebox.showwarning("Complete", f"Output:\n{out_path}\nFiltered: failed (see log)")
            return
        filtered_rows = None
        try:
            filtered_rows = count_tsv_rows(filtered_path)
        except Exception as exc:
            log(f"Filtered TSV count failed: {exc}")
        summary_path, summary_text = write_summary(
            out_dir,
            in_path,
            out_path,
            vlen_min,
            str(IGBLAST),
            str(REF_DIR_FULL),
            num_threads,
            v_penalty,
            extend_align5end,
            input_records=input_records,
            output_rows=output_rows,
            filtered_rows=filtered_rows,
            filter_summary=summary,
            filtered_path=filtered_path,
        )
        LAST_RUN_SUMMARY = summary_text
        messagebox.showinfo(
            "Complete",
            f"Output:\n{out_path}\nFiltered:\n{filtered_path}\nSummary:\n{summary_path}\n{summary}",
        )
    else:
        messagebox.showerror("Error", "IgBLAST failed. Check log.")


def main():
    root = tk.Tk()
    root.title("Merged FASTA -> AIRR outfmt 19")
    root.geometry("900x620")

    frame = tk.Frame(root, padx=10, pady=10)
    frame.pack(fill=tk.BOTH, expand=True)

    config = load_config()
    apply_config(config)

    tk.Label(frame, text="Merged FASTA (extendedFrags.fasta):").grid(row=0, column=0, sticky="w")
    input_var = tk.StringVar()
    entry = tk.Entry(frame, textvariable=input_var, width=80)
    entry.grid(row=1, column=0, padx=(0, 8), sticky="we")

    def browse_input():
        path = filedialog.askopenfilename(
            title="Select FASTA",
            filetypes=[("FASTA", "*.fasta;*.fa;*.fna"), ("All", "*.*")],
        )
        if path:
            input_var.set(path)

    tk.Button(frame, text="Browse", command=browse_input).grid(row=1, column=1, sticky="e")

    tk.Label(frame, text="IgBLAST exe:").grid(row=2, column=0, sticky="w")
    igblast_var = tk.StringVar(value=config.get("igblast_path", str(IGBLAST)))
    igblast_entry = tk.Entry(frame, textvariable=igblast_var, width=80)
    igblast_entry.grid(row=3, column=0, padx=(0, 8), sticky="we")

    def browse_igblast():
        path = filedialog.askopenfilename(
            title="Select igblastn.exe",
            filetypes=[("igblastn.exe", "igblastn.exe"), ("EXE", "*.exe"), ("All", "*.*")],
        )
        if path:
            igblast_var.set(path)

    tk.Button(frame, text="Browse", command=browse_igblast).grid(row=3, column=1, sticky="e")

    tk.Label(frame, text="Reference data folder:").grid(row=4, column=0, sticky="w")
    ref_value = config.get("ref_dir", "")
    if ref_value and not Path(ref_value).exists():
        ref_value = ""
    if not ref_value:
        ref_value = str(REF_DIR_FULL)
    ref_var = tk.StringVar(value=ref_value)
    ref_preset_var = tk.StringVar(value=preset_label_for_path(ref_value))
    preset_labels = [label for label, _ in REFDATA_PRESETS]

    def apply_ref_preset(*_):
        label = ref_preset_var.get()
        for opt_label, opt_path in REFDATA_PRESETS:
            if opt_label == label and opt_path:
                ref_var.set(str(opt_path))
                return

    def sync_ref_preset(*_):
        label = preset_label_for_path(ref_var.get())
        if ref_preset_var.get() != label:
            ref_preset_var.set(label)

    ref_var.trace_add("write", sync_ref_preset)

    preset_frame = tk.Frame(frame)
    tk.Label(preset_frame, text="Preset:").pack(side=tk.LEFT)
    tk.OptionMenu(preset_frame, ref_preset_var, *preset_labels, command=apply_ref_preset).pack(side=tk.LEFT)
    preset_frame.grid(row=4, column=1, sticky="e")

    ref_entry = tk.Entry(frame, textvariable=ref_var, width=80)
    ref_entry.grid(row=5, column=0, padx=(0, 8), sticky="we")

    def browse_ref():
        path = filedialog.askdirectory(title="Select reference data folder")
        if path:
            ref_var.set(path)

    tk.Button(frame, text="Browse", command=browse_ref).grid(row=5, column=1, sticky="e")

    tk.Label(frame, text="Threads (-num_threads):").grid(row=6, column=0, sticky="w")
    threads_value = config.get("threads", THREAD_DEFAULT)
    threads_var = tk.StringVar(value="" if threads_value is None else str(threads_value))
    threads_entry = tk.Entry(frame, textvariable=threads_var, width=10)
    threads_entry.grid(row=7, column=0, sticky="w")

    tk.Label(frame, text="V_penalty:").grid(row=8, column=0, sticky="w")
    v_penalty_value = config.get("v_penalty", V_PENALTY_DEFAULT)
    v_penalty_var = tk.StringVar(value="" if v_penalty_value is None else str(v_penalty_value))
    v_penalty_entry = tk.Entry(frame, textvariable=v_penalty_var, width=10)
    v_penalty_entry.grid(row=9, column=0, sticky="w")

    extend_value = config.get("extend_align5end", EXTEND_ALIGN5END_DEFAULT)
    extend_var = tk.BooleanVar(value=bool(extend_value))
    tk.Checkbutton(
        frame,
        text="Extend align 5' end (-extend_align5end)",
        variable=extend_var,
    ).grid(row=10, column=0, columnspan=2, sticky="w")

    tk.Label(frame, text="Filter (vlen_ungapped):").grid(row=11, column=0, sticky="w")
    filter_labels = [label for label, _ in FILTER_OPTIONS]
    filter_var = tk.StringVar(value=filter_labels[0])
    tk.OptionMenu(frame, filter_var, *filter_labels).grid(row=11, column=1, sticky="w")

    log_box = tk.Text(frame, height=10)
    log_box.grid(row=12, column=0, columnspan=2, pady=(10, 0), sticky="nsew")

    def log(msg):
        log_box.insert(tk.END, msg + "\n")
        log_box.see(tk.END)

    def update_settings():
        global IGBLAST, REF_DIR_FULL, REF_DIR_USE
        igblast_path = igblast_var.get().strip() or str(DEFAULT_IGBLAST)
        ref_path = ref_var.get().strip() or str(DEFAULT_REF_DIR_FULL)
        try:
            threads = parse_threads(threads_var.get())
            v_penalty = parse_v_penalty(v_penalty_var.get())
        except ValueError as exc:
            messagebox.showerror("Settings", str(exc))
            return None, None, None, False
        extend_align5end = bool(extend_var.get())
        IGBLAST = Path(igblast_path)
        REF_DIR_FULL = Path(ref_path)
        REF_DIR_USE = None
        save_config(igblast_path, ref_path, threads, v_penalty, extend_align5end)
        return threads, v_penalty, extend_align5end, True

    def run():
        label = filter_var.get()
        vlen_min = None
        for opt_label, opt_value in FILTER_OPTIONS:
            if opt_label == label:
                vlen_min = opt_value
                break
        threads, v_penalty, extend_align5end, ok = update_settings()
        if not ok:
            return
        run_igblast(
            input_var.get().strip(),
            vlen_min,
            threads,
            v_penalty,
            extend_align5end,
            log,
        )

    def save_settings():
        _, _, _, ok = update_settings()
        if ok:
            messagebox.showinfo("Settings", "Settings saved.")

    def copy_summary():
        if not LAST_RUN_SUMMARY:
            messagebox.showinfo("Copy summary", "No summary to copy yet.")
            return
        root.clipboard_clear()
        root.clipboard_append(LAST_RUN_SUMMARY)
        root.update()
        messagebox.showinfo("Copy summary", "Copied to clipboard.")

    button_frame = tk.Frame(frame)
    button_frame.grid(row=13, column=0, columnspan=2, pady=10, sticky="we")
    tk.Button(button_frame, text="Run", command=run).pack(side=tk.LEFT)
    tk.Button(button_frame, text="Save settings", command=save_settings).pack(side=tk.LEFT, padx=(8, 0))
    tk.Button(button_frame, text="Copy summary", command=copy_summary).pack(side=tk.RIGHT)

    frame.columnconfigure(0, weight=1)
    frame.rowconfigure(12, weight=1)

    root.mainloop()


if __name__ == "__main__":
    main()
