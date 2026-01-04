# merged_fasta → AIRR outfmt 19 (IgBLAST GUI)

マージ済みFASTA（extendedFrags.fasta）を入力し、IgBLASTでAIRR outfmt 19のTSVを出力するGUIです。

## できること
- マージ済みFASTAを選択してIgBLASTを実行
- AIRR outfmt 19 TSVを出力

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
3. Runを押す
4. `result_AIRR_outfmat` に `*.igblast.airr.tsv` が出力される

## 補足
- 参照DBは検体固有ではなく「ヒトIgH用の一般的DB」です。
- 参照DBを更新したい場合は、IMGTのFASTAを更新し、makeblastdbを再実行してください。
