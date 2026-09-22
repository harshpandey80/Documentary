@echo off
echo ========================================================
echo Launching Meta AI with DocStudio Persistent Profile
echo ========================================================
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --user-data-dir="%~dp0cache\browser_profiles\meta_ai" --new-window "https://www.meta.ai"
exit
