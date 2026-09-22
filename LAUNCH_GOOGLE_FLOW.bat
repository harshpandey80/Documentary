@echo off
echo ========================================================
echo Launching Google Flow with DocStudio Persistent Profile
echo ========================================================
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --user-data-dir="%~dp0cache\browser_profiles\google_flow" --new-window "https://flow.google.com/project/5db9bfdb-84ec-4a87-b006-a3345400a62b"
exit
