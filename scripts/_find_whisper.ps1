Write-Host "=== Searching common locations for whisper ==="

$roots = @(
  "$env:USERPROFILE",
  "$env:LOCALAPPDATA",
  "C:\Program Files",
  "C:\Program Files (x86)",
  "C:\tools",
  "C:\whisper"
)

Write-Host "`n--- whisper.exe / main.exe / whisper-cli.exe ---"
foreach ($r in $roots) {
  if (Test-Path $r) {
    Get-ChildItem -Path $r -Recurse -ErrorAction SilentlyContinue -Include 'whisper.exe','whisper-cli.exe','main.exe','faster-whisper*.exe','whisper-faster.exe' |
      Where-Object { $_.FullName -notmatch 'node_modules|\\\.git\\' } |
      Select-Object FullName, Length |
      Format-Table -AutoSize
  }
}

Write-Host "`n--- ggml / .bin / .pt model files ---"
foreach ($r in $roots) {
  if (Test-Path $r) {
    Get-ChildItem -Path $r -Recurse -ErrorAction SilentlyContinue -Include 'ggml-*.bin','*whisper*.pt','*whisper*.bin' |
      Where-Object { $_.FullName -notmatch 'node_modules|\\\.git\\' -and $_.Length -gt 10MB } |
      Select-Object FullName, @{N='SizeMB';E={[math]::Round($_.Length/1MB,1)}} |
      Format-Table -AutoSize
  }
}

Write-Host "`n--- pip packages with 'whisper' ---"
pip list 2>$null | Select-String -Pattern 'whisper|ffmpeg' -SimpleMatch

Write-Host "`n--- ffmpeg locations ---"
foreach ($r in $roots) {
  if (Test-Path $r) {
    Get-ChildItem -Path $r -Recurse -ErrorAction SilentlyContinue -Include 'ffmpeg.exe' |
      Where-Object { $_.FullName -notmatch 'node_modules|\\\.git\\' } |
      Select-Object FullName |
      Format-Table -AutoSize
  }
}

Write-Host "`n--- python in PATH ---"
Get-Command python -ErrorAction SilentlyContinue | Select-Object Source
python --version 2>&1
