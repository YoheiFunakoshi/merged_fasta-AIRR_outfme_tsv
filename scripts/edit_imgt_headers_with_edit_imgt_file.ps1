param(
    [Parameter(Mandatory = $true)]
    [string]$EditImgtFile,
    [Parameter(Mandatory = $true)]
    [string]$InputDir,
    [Parameter(Mandatory = $true)]
    [string]$OutputDir,
    [string]$Perl = "perl"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not (Test-Path $EditImgtFile)) {
    throw "edit_imgt_file.pl not found: $EditImgtFile"
}
if (-not (Test-Path $InputDir)) {
    throw "Input directory not found: $InputDir"
}

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

$stems = @("IGHV", "IGHD", "IGHJ")
foreach ($stem in $stems) {
    $candidates = @("IMGT_$stem.fasta", "$stem.fasta")
    $inputPath = $null
    foreach ($name in $candidates) {
        $candidatePath = Join-Path $InputDir $name
        if (Test-Path $candidatePath) {
            $inputPath = $candidatePath
            break
        }
    }
    if (-not $inputPath) {
        $names = $candidates -join ", "
        throw "Missing input for $stem. Expected one of: $names in $InputDir"
    }

    $baseName = [System.IO.Path]::GetFileNameWithoutExtension($inputPath)
    $outputPath = Join-Path $OutputDir ($baseName + ".imgt.fasta")

    & $Perl $EditImgtFile $inputPath | Set-Content -Path $outputPath -Encoding Ascii
    Write-Host "Wrote $outputPath"
}
