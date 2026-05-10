$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$env:USERPROFILE\Desktop\scribe.lnk")
$Shortcut.TargetPath = "C:\Users\rayya\Desktop\scribe\run.bat"
$Shortcut.WorkingDirectory = "C:\Users\rayya\Desktop\scribe"
$Shortcut.WindowStyle = 7
$Shortcut.Description = "Scribe — local voice to text"
$Shortcut.Save()
Write-Host "Done"
