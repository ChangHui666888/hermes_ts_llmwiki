@echo off
chcp 65001 >nul
REM Create Windows Scheduled Task for Wiki auto-sync
schtasks /Create /SC MINUTE /MO 30 /TN "HermesWiki-Sync" /TR "C:\Program Files\Git\bin\bash.exe -c \"cd /c/Users/ChangHui/wiki && bash scripts/wiki-sync.sh\"" /IT /RL HIGHEST /F
echo.
schtasks /Query /TN "HermesWiki-Sync" /FO LIST
pause
