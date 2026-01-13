# merged_fasta → AIRR outfmt 19 (IgBLAST GUI)

マージ済みFASTA（extendedFrags.fasta）を入力し、IgBLASTでAIRR outfmt 19のTSVを出力するGUIです。

## できること
- マージ済みFASTAを選択してIgBLASTを実行
- AIRR outfmt 19 TSVを出力
- vlen_ungapped フィルタをかけた別TSVを任意で出力（元TSVは保持）
- 実行ごとに結果とsummaryを1フォルダにまとめて出力
- IgBLAST/参照データのパスをGUIで選択して保存
- `-num_threads` を指定して高速化（任意）

## アプリの場所
- 起動用ショートカット: `AIRR_igblast_app.lnk`
- 本体スクリプト: `AIRR_igblast_app.pyw`
- 出力先: `result_AIRR_outfmat/`

## 前提（インストール済み）
- IgBLAST: `C:/Program Files/NCBI/igblast-1.21.0/bin/igblastn.exe`

## 参照データの場所（デスクトップ上）
`C:/Users/Yohei Funakoshi/Desktop/IgBlast用参照データ`

このフォルダは **アプリから参照される必須データ** です。削除しないでください。  
フォルダ名/場所を変更した場合は `AIRR_igblast_app.pyw` の `REF_DIR_FULL` を更新してください。  
非ASCIIパスが原因で参照エラーになる場合、アプリが `refdata` というASCII名のジャンクションを自動作成します。

### フォルダ構成と意図
- `db/` : IMGTの参照FASTAから作ったBLASTデータベース（索引ファイル群）
- `IMGT_raw/` : IMGTから取得した元のFASTA（V/D/J 生殖系列配列）
- `internal_data/` : IgBLAST同梱の内部注釈データ（IMGT番号やFWR/CDR境界の補助）
- `optional_file/` : J遺伝子のフレーム/ CDR3終端などの補助情報（-auxiliary_data で指定）

## 再現手順（参照データの作り方）

### 1) IgBLASTのインストール
- 公式: https://ncbi.github.io/igblast/
- インストール先: `C:/Program Files/NCBI/igblast-1.21.0/`

### 2) 参照データフォルダを作成
```
C:/Users/Yohei Funakoshi/Desktop/IgBlast用参照データ
```

### 3) internal_data / optional_file をコピー
IgBLASTインストール先からコピーします。
```
C:/Program Files/NCBI/igblast-1.21.0/internal_data
C:/Program Files/NCBI/igblast-1.21.0/optional_file
```

### 4) IMGTからヒトIgHのV/D/J FASTAを取得
IMGTのページから Human の IGHV / IGHD / IGHJ をダウンロードし、以下に保存します。
```
C:/Users/Yohei Funakoshi/Desktop/IgBlast用参照データ/IMGT_raw
```
ファイル名例:
- `IMGT_IGHV.fasta`
- `IMGT_IGHD.fasta`
- `IMGT_IGHJ.fasta`

### 5) IMGTヘッダを簡略化（imgt.fasta作成）
IMGTのヘッダをIgBLASTが扱いやすい形式にします。

**Python例（Perlが無い場合）**
```python
from pathlib import Path

ref = Path(r"C:/Users/Yohei Funakoshi/Desktop/IgBlast用参照データ")
inputs = [
    ref/"IMGT_raw"/"IMGT_IGHV.fasta",
    ref/"IMGT_raw"/"IMGT_IGHD.fasta",
    ref/"IMGT_raw"/"IMGT_IGHJ.fasta",
]

for inp in inputs:
    outp = inp.with_suffix(".imgt.fasta")
    with inp.open("r", encoding="utf-8", errors="ignore") as fin, outp.open("w", encoding="ascii", errors="ignore") as fout:
        for line in fin:
            if line.startswith(">"):
                parts = line[1:].strip().split("|")
                gene = parts[1].strip() if len(parts) >= 2 and parts[1].strip() else line[1:].strip()
                fout.write(">" + gene + "\n")
            else:
                seq = line.strip().upper()
                if seq:
                    fout.write(seq + "\n")
```

出力例:
- `IMGT_IGHV.imgt.fasta`
- `IMGT_IGHD.imgt.fasta`
- `IMGT_IGHJ.imgt.fasta`

### 6) makeblastdbでDB作成
```
"C:/Program Files/NCBI/igblast-1.21.0/bin/makeblastdb.exe" -parse_seqids -dbtype nucl -in IMGT_IGHV.imgt.fasta -out db/IMGT_IGHV.imgt
"C:/Program Files/NCBI/igblast-1.21.0/bin/makeblastdb.exe" -parse_seqids -dbtype nucl -in IMGT_IGHD.imgt.fasta -out db/IMGT_IGHD.imgt
"C:/Program Files/NCBI/igblast-1.21.0/bin/makeblastdb.exe" -parse_seqids -dbtype nucl -in IMGT_IGHJ.imgt.fasta -out db/IMGT_IGHJ.imgt
```

## アプリの使い方
1. `AIRR_igblast_app.lnk` をダブルクリック
2. マージ済みFASTA（extendedFrags.fasta）を選択
3. IgBLAST exe / Reference data folder / Threads を必要に応じて設定
4. Filter（vlen_ungapped）を選択（任意、なし/80/100/120/150）
5. Runを押す（設定は自動保存）
6. `result_AIRR_outfmat/<入力名>__vlen{N or nofilter}__YYYYmmdd_HHMMSS/` が作成される
7. フォルダ内に `<入力名>.igblast.airr.tsv` と `summary.txt` が出力される
8. フィルタ有効時は `<入力名>.igblast.airr.vlenmin{N}.tsv` が追加で出力される
9. 必要なら「Copy summary」でフィルタ結果サマリをクリップボードにコピー

### 画面項目の意味
- Merged FASTA: マージ済みFASTA（extendedFrags.fasta）を指定します。
- IgBLAST exe: `igblastn.exe` のパスを指定します。
- Reference data folder: `db/`、`internal_data/`、`optional_file/` を含む参照データのルートフォルダです。
- Threads (-num_threads): IgBLASTのスレッド数です。空欄ならデフォルト動作です。
- Filter (vlen_ungapped): `v_sequence_alignment` のギャップ除外長でフィルタします（なし/80/100/120/150）。
- Log: 実行ログと警告を表示します。

### ボタンの使い方
- Run: 設定を保存してIgBLASTを実行します。
- Save settings: 実行せず設定だけ保存します。
- Copy summary: `summary.txt` と同じ内容をクリップボードへコピーします。

### 設定の保存
- 画面の設定は `config.json` に保存されます（Run/Save settingsで更新）。

### 出力フォルダの中身
- `<入力名>.igblast.airr.tsv`: 元のIgBLAST出力（変更しない）
- `<入力名>.igblast.airr.vlenmin{N}.tsv`: フィルタ版（N選択時のみ）
- `summary.txt`: 入力/出力/フィルタ条件/件数サマリ

### summary.txt の例
```
Run folder: ...\result_AIRR_outfmat\<入力名>__vlen150__YYYYmmdd_HHMMSS
Input: C:\path\to\input.fasta
Output: ...\<入力名>.igblast.airr.tsv
IgBLAST: C:\Program Files\NCBI\igblast-1.21.0\bin\igblastn.exe
Refdata: C:\Users\Yohei Funakoshi\Desktop\IgBlast用参照データ
Threads: 4
Filter: vlen_ungapped >= 150
Filtered: ...\<入力名>.igblast.airr.vlenmin150.tsv
Filter vlen_ungapped >= 150: kept 17096/29395, missing 46
Timestamp: 2026-01-13 21:47:27
```

## 補足
- 参照DBは検体固有ではなく「ヒトIgH用の一般的DB」です。
- 参照DBを更新したい場合は、IMGTのFASTAを更新し、makeblastdbを再実行してください。

## 注意（vlen_ungapped フィルタ）
- 元TSVは変更せず、フィルタ版は実行フォルダ内に保存されます。
- 判定は `v_sequence_alignment` から `vlen_ungapped` を算出します（`NA`/空は除外）。
- フィルタを「なし」にすると元TSVのみ出力します。
- Windowsのパス長制限を避けるため、フォルダ名が長い場合は自動的に短縮されることがあります。
- Windowsのパス長制限を避けるため、ファイル名が長い場合は自動的に短縮されることがあります。
