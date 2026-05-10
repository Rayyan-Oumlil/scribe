Get-ChildItem 'C:\Users\rayya\Downloads' -File |
  Where-Object { $_.Extension -match '\.(mp3|wav|m4a|ogg|flac|aac|wma|webm|mp4|mov)$' } |
  Select-Object Name, LastWriteTime, @{N='SizeMB';E={[math]::Round($_.Length/1MB,2)}} |
  Sort-Object LastWriteTime -Descending |
  Format-Table -AutoSize

Write-Host "---"
Write-Host "whisper:"
Get-Command whisper -ErrorAction SilentlyContinue | Select-Object Source
Write-Host "ffmpeg:"
Get-Command ffmpeg -ErrorAction SilentlyContinue | Select-Object Source
Write-Host "python whisper module:"
python -c "import whisper, sys; print(whisper.__file__)" 2>&1
