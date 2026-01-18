# merged_fasta → AIRR outfmt 19 (IgBLAST GUI)

マージ済みFASTA（extendedFrags.fasta）を入力し、IgBLASTでAIRR outfmt 19のTSVを出力するGUIです。

## できること
- マージ済みFASTAを選択してIgBLASTを実行
- AIRR outfmt 19 TSVを出力
- vlen_ungapped フィルタをかけた別TSVを任意で出力（元TSVは保持）
- 実行ごとに結果とsummaryを1フォルダにまとめて出力
- IgBLAST/参照データのパスをGUIで選択して保存
- `-num_threads` を指定して高速化（任意）
- `-V_penalty` / `-extend_align5end` を任意で指定

## アプリの場所
- 起動用ショートカット: `AIRR_igblast_app.lnk`
- 本体スクリプト: `AIRR_igblast_app.pyw`
- 出力先: `result_AIRR_outfmat/`

## 前提（インストール済み）
- IgBLAST: `C:/Program Files/NCBI/igblast-1.21.0/bin/igblastn.exe`

## 参照データの場所（デスクトップ上）
- デフォルト（edit_imgt_file.pl DB）: `C:/Users/Yohei Funakoshi/Desktop/IgBlast_refdata_edit_imgt`
- Legacy（python DB）: `C:/Users/Yohei Funakoshi/Desktop/IgBlast用参照データ`

このフォルダは **アプリから参照される必須データ** です。削除しないでください。  
GUIの「Preset」でデフォルト/Legacyを切り替えできます。  
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
C:/Users/Yohei Funakoshi/Desktop/IgBlast_refdata_edit_imgt
```
（Legacyを残す場合は `C:/Users/Yohei Funakoshi/Desktop/IgBlast用参照データ` も保持）

### 3) internal_data / optional_file をコピー
IgBLASTインストール先からコピーします。
```
C:/Program Files/NCBI/igblast-1.21.0/internal_data
C:/Program Files/NCBI/igblast-1.21.0/optional_file
```

### 4) IMGTからヒトIgHのV/D/J FASTAを取得
IMGTのページから Human の IGHV / IGHD / IGHJ をダウンロードし、以下に保存します。
```
C:/Users/Yohei Funakoshi/Desktop/IgBlast_refdata_edit_imgt/IMGT_raw
```
ファイル名例:
- `IMGT_IGHV.fasta`
- `IMGT_IGHD.fasta`
- `IMGT_IGHJ.fasta`

### 5) IMGTヘッダを簡略化（imgt.fasta作成）
IMGTのヘッダをIgBLASTが扱いやすい形式にします。**デフォルトは edit_imgt_file.pl** です。

**edit_imgt_file.pl（推奨）**
```
perl "C:/Program Files/NCBI/igblast-1.21.0/bin/edit_imgt_file.pl" IMGT_IGHV.fasta > IMGT_IGHV.imgt.fasta
perl "C:/Program Files/NCBI/igblast-1.21.0/bin/edit_imgt_file.pl" IMGT_IGHD.fasta > IMGT_IGHD.imgt.fasta
perl "C:/Program Files/NCBI/igblast-1.21.0/bin/edit_imgt_file.pl" IMGT_IGHJ.fasta > IMGT_IGHJ.imgt.fasta
```
バッチ用ラッパー（PowerShell）: `scripts/edit_imgt_headers_with_edit_imgt_file.ps1`
```
powershell -ExecutionPolicy Bypass -File scripts/edit_imgt_headers_with_edit_imgt_file.ps1 `
  -EditImgtFile "C:/Program Files/NCBI/igblast-1.21.0/bin/edit_imgt_file.pl" `
  -InputDir "C:/path/to/IMGT_raw" `
  -OutputDir "C:/path/to/IMGT_edited"
```

**Python代替（必要時のみ）**
Perlが使えない場合に限り `scripts/edit_imgt_headers_python.py` を使用します。  
他者と共有する場合は「edit_imgt_file.pl と同等変換」であることを明記し、スクリプト/実行コマンドも共有してください。
```
python scripts/edit_imgt_headers_python.py --input-dir "C:/path/to/IMGT_raw" --output-dir "C:/path/to/IMGT_edited"
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
3. IgBLAST exe / Preset / Reference data folder / Threads を必要に応じて設定
4. Filter（vlen_ungapped）を選択（任意、なし/80/100/120/150）
5. Runを押す（設定は自動保存）
6. `result_AIRR_outfmat/<入力名>__vlen{N or nofilter}__YYYYmmdd_HHMMSS/` が作成される
7. フォルダ内に `<入力名>.igblast.airr.tsv` と `summary.txt` が出力される
8. フィルタ有効時は `<入力名>.igblast.airr.vlenmin{N}.tsv` が追加で出力される
9. 必要なら「Copy summary」でフィルタ結果サマリをクリップボードにコピー

### 画面項目の意味
- Merged FASTA: マージ済みFASTA（extendedFrags.fasta）を指定します。
- IgBLAST exe: `igblastn.exe` のパスを指定します。
- Preset: 参照DBのプリセットです（edit_imgt_file.pl DB / Legacy DB / Custom）。
- Reference data folder: `db/`、`internal_data/`、`optional_file/` を含む参照データのルートフォルダです。
- Threads (-num_threads): IgBLASTのスレッド数です。空欄ならデフォルト動作です。
- V_penalty: Vアラインのミスマッチペナルティです（例: -1, -3）。空欄ならデフォルト動作です。
- Extend align 5' end: 5'側のアライン表示を拡張します（表示のみ）。
- Filter (vlen_ungapped): `v_sequence_alignment` のギャップ除外長でフィルタします（なし/80/100/120/150）。
- Log: 実行ログと警告を表示します。

### 各項目のデフォルト/意義/注意点
- Merged FASTA
  - デフォルト: 空欄（毎回選択）
  - 意義: 入力FASTAを指定
  - 注意点: マージ済みFASTA（extendedFrags.fasta など）を選択
- IgBLAST exe
  - デフォルト: 既定パス（未設定なら `C:/Program Files/NCBI/igblast-1.21.0/bin/igblastn.exe`）
  - 意義: IgBLAST本体の場所を指定
  - 注意点: バージョン違いで出力が変わる場合があるため、変更したら summary を確認
- Reference data folder
  - デフォルト: Preset=edit_imgt_file.pl DB の場合 `C:/Users/Yohei Funakoshi/Desktop/IgBlast_refdata_edit_imgt`
  - 意義: V/D/J DB と補助データを参照
  - 注意点: `db/` と `optional_file/` が必要
- Preset
  - デフォルト: edit_imgt_file.pl DB
  - 意義: 参照DBをワンクリックで切り替え
  - 注意点: Legacy DB は旧手順再現/比較用。Custom を選ぶ場合は参照フォルダの中身を必ず確認
- Threads (-num_threads)
  - デフォルト: 空欄（IgBLASTのデフォルト動作）
  - 意義: 速度改善（CPU並列）
  - 注意点: 入れすぎると他作業が遅くなる
- V_penalty
  - デフォルト: 空欄（IgBLASTのデフォルト動作）
  - 意義: 「短い高類似」より「長い一致」を優先しやすくする調整
  - 注意点: v_identity/SHMの解釈に影響し得るため、変更したら条件を記録
- Extend align 5' end
  - デフォルト: OFF
  - 意義: 5'側の表示を拡張（確認用途）
  - 注意点: v_sequence_alignment が長く見えるため、vlen_ungapped フィルタと併用時は注意
- Filter (vlen_ungapped)
  - デフォルト: なし（元TSVのみ出力）
  - 意義: 短いVアラインを除外した別TSVを作成
  - 注意点: `NA`/空は除外されるため、件数差が出る

### ボタンの使い方
- Run: 設定を保存してIgBLASTを実行します。
- Save settings: 実行せず設定だけ保存します。
- Copy summary: `summary.txt` と同じ内容をクリップボードへコピーします。

### 設定の保存
- 画面の設定は `config.json` に保存されます（Run/Save settingsで更新）。
- `config.json` はPC固有の設定のため、共有用にはREADME/手順書に条件を記載してください。

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
Refdata: C:\Users\Yohei Funakoshi\Desktop\IgBlast_refdata_edit_imgt
Input FASTA records: 110830
Output TSV rows: 110830
Threads: 4
V_penalty: -1
Extend_align5end: on
Filter: vlen_ungapped >= 150
Filtered: ...\<入力名>.igblast.airr.vlenmin150.tsv
Filtered TSV rows: 17096
Filter vlen_ungapped >= 150: kept 17096/29395, missing 46
Timestamp: 2026-01-13 21:47:27
```

## 補足
- 参照DBは検体固有ではなく「ヒトIgH用の一般的DB」です。
- デフォルトは edit_imgt_file.pl 由来DBです。Legacy DB は旧手順の再現/比較用として保持しています。
- 参照DBを更新したい場合は、IMGTのFASTAを更新し、makeblastdbを再実行してください。

## 注意（vlen_ungapped フィルタ）
- 元TSVは変更せず、フィルタ版は実行フォルダ内に保存されます。
- 判定は `v_sequence_alignment` から `vlen_ungapped` を算出します（`NA`/空は除外）。
- フィルタを「なし」にすると元TSVのみ出力します。
- Windowsのパス長制限を避けるため、フォルダ名が長い場合は自動的に短縮されることがあります。
- Windowsのパス長制限を避けるため、ファイル名が長い場合は自動的に短縮されることがあります。
