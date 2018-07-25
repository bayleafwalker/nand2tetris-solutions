cd /d %~dp0

PowerShell.exe -Command "& Get-ChildItem .\asm -Filter *.asm | Foreach-Object {	python ..\assembler.py $_.FullName -d .\prospective\}"

:: Using rdiff (in path) by https://gist.github.com/cchamberlain/883959151aa1162e73f1
PowerShell.exe -Command "& rdiff .\preassembled, .\prospective"

PAUSE