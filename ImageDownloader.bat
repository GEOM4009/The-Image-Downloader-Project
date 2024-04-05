@echo off
:start
"C:\Users\zachs\anaconda3\envs\geom4009\python.exe" "C:\Users\zachs\Documents\GitHub\The-Image-Downloader-Project\04-02-2024\ImageDownloaderProject.py" "C:\Users\zachs\Documents\GitHub\The-Image-Downloader-Project\04-02-2024\config.cfg"
timeout /t 300 /nobreak >nul
goto start
