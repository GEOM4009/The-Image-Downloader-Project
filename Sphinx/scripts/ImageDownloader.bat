@echo off
:start
"C:\Users\zachs\anaconda3\envs\imagedownloader\python.exe" "C:\Users\zachs\Documents\GitHub\The-Image-Downloader-Project\ImageDownloaderProject.py" "C:\Users\zachs\Documents\GitHub\The-Image-Downloader-Project\config.cfg"
timeout /t 300 /nobreak >nul
goto start