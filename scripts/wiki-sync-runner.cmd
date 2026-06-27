@echo off
chcp 65001 >nul
cd /d C:\Users\ChangHui\wiki
C:\Program Files\Git\bin\bash.exe -c "cd /c/Users/ChangHui/wiki && bash scripts/wiki-sync.sh"
