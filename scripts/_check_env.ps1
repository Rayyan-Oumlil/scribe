python -c "import faster_whisper, sys; print('faster-whisper at:', faster_whisper.__file__); print('python:', sys.executable)" 2>&1
Write-Host "---"
Get-ChildItem 'C:\Users\rayya\Desktop\scribe' -Directory -Force |
  Where-Object { $_.Name -match 'venv|env' } |
  Select-Object FullName
Write-Host "---"
if (Test-Path 'C:\Users\rayya\Desktop\scribe\run.bat') {
  Get-Content 'C:\Users\rayya\Desktop\scribe\run.bat'
}
