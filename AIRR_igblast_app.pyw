# -*- coding: utf-8 -*-
import os
import subprocess
from pathlib import Path
import ctypes
import csv
import tkinter as tk
from tkinter import filedialog, messagebox

APP_DIR = Path(__file__).resolve().parent
RESULT_DIR = APP_DIR / "result_AIRR_outfmat"
# Full path to reference data (can include non-ASCII).
REF_DIR_FULL = Path(r"C:\Users\Yohei Funakoshi\Desktop\IgBlast用参照データ")
IGBLAST = Path(r"C:\Program Files\NCBI\igblast-1.21.0\bin\igblastn.exe")
REF_DIR_USE = None

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


def short_path(path_str):
    buf = ctypes.create_unicode_buffer(260)
    ret = KERNEL32.GetShortPathNameW(path_str, buf, 260)
    return buf.value if ret else path_str


def get_ref_dir():
    global REF_DIR_USE
    if REF_DIR_USE is not None:
        return REF_DIR_USE

    ref_short = Path(short_path(str(REF_DIR_FULL)))
    if (ref_short / "db").exists():
        REF_DIR_USE = ref_short
        return REF_DIR_USE

    # Create an ASCII junction under the app folder if 8.3 short path isn't available.
    junction = APP_DIR / "refdata"
    if not junction.exists():
        try:
            subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(junction), str(REF_DIR_FULL)],
                capture_output=True,
                text=True,
            )
        except Exception:
            pass
    if junction.exists():
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
    for name in ("IMGT_IGHV.imgt.nsq", "IMGT_IGHD.imgt.nsq", "IMGT_IGHJ.imgt.nsq"):
        if not (db_dir / name).exists():
            missing.append(str(db_dir / name))
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


def run_igblast(input_path, vlen_min, log):
    if not check_prereq():
        return
    if not input_path:
        messagebox.showwarning("Input", "Please select a FASTA file.")
        return
    in_path = Path(input_path)
    if not in_path.exists():
        messagebox.showerror("Input", "Input file not found.")
        return

    RESULT_DIR.mkdir(exist_ok=True)
    out_name = in_path.stem + ".igblast.airr.tsv"
    out_path = RESULT_DIR / out_name

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
        if vlen_min is None:
            messagebox.showinfo("Complete", f"Output:\n{out_path}")
            return
        filtered_dir = RESULT_DIR / f"vlen{vlen_min}"
        filtered_dir.mkdir(exist_ok=True)
        filtered_path = filtered_dir / (out_path.stem + f".vlenmin{vlen_min}.tsv")
        log("Filtering TSV by vlen_ungapped...")
        try:
            summary = filter_airr_tsv(out_path, filtered_path, vlen_min, log)
        except Exception as exc:
            log(f"Filter error: {exc}")
            messagebox.showwarning("Complete", f"Output:\n{out_path}\nFiltered: failed (see log)")
            return
        messagebox.showinfo(
            "Complete",
            f"Output:\n{out_path}\nFiltered:\n{filtered_path}\n{summary}",
        )
    else:
        messagebox.showerror("Error", "IgBLAST failed. Check log.")


def main():
    root = tk.Tk()
    root.title("Merged FASTA -> AIRR outfmt 19")
    root.geometry("720x360")

    frame = tk.Frame(root, padx=10, pady=10)
    frame.pack(fill=tk.BOTH, expand=True)

    tk.Label(frame, text="Merged FASTA (extendedFrags.fasta):").grid(row=0, column=0, sticky="w")
    input_var = tk.StringVar()
    entry = tk.Entry(frame, textvariable=input_var, width=80)
    entry.grid(row=1, column=0, padx=(0, 8), sticky="we")

    def browse():
        path = filedialog.askopenfilename(
            title="Select FASTA",
            filetypes=[("FASTA", "*.fasta;*.fa;*.fna"), ("All", "*.*")],
        )
        if path:
            input_var.set(path)

    tk.Button(frame, text="Browse", command=browse).grid(row=1, column=1, sticky="e")

    tk.Label(frame, text="Filter (vlen_ungapped):").grid(row=2, column=0, sticky="w")
    filter_labels = [label for label, _ in FILTER_OPTIONS]
    filter_var = tk.StringVar(value=filter_labels[0])
    tk.OptionMenu(frame, filter_var, *filter_labels).grid(row=2, column=1, sticky="w")

    log_box = tk.Text(frame, height=10)
    log_box.grid(row=3, column=0, columnspan=2, pady=(10, 0), sticky="nsew")

    def log(msg):
        log_box.insert(tk.END, msg + "\n")
        log_box.see(tk.END)

    def run():
        label = filter_var.get()
        vlen_min = None
        for opt_label, opt_value in FILTER_OPTIONS:
            if opt_label == label:
                vlen_min = opt_value
                break
        run_igblast(input_var.get().strip(), vlen_min, log)

    tk.Button(frame, text="Run", command=run).grid(row=4, column=0, pady=10, sticky="w")

    frame.columnconfigure(0, weight=1)
    frame.rowconfigure(3, weight=1)

    root.mainloop()


if __name__ == "__main__":
    main()
