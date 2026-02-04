@echo off
SET CONTAINER_NAME=arthur-prime
SET URL=http://localhost:8000

echo Checking if %CONTAINER_NAME% is already active...

:: Check if the container name exists in the 'docker ps' list
wsl docker ps --format "{{.Names}}" | findstr /X "%CONTAINER_NAME%" > nul

if %ERRORLEVEL% EQU 0 (
    echo [!] Container is already running. Skipping start...
) else (
    echo [1/2] Starting Docker container in WSL...
    wsl docker run --name %CONTAINER_NAME% --gpus all -d --rm -p 8000:8000 project-arthur-prod
    
    :: Give the container a moment to spin up the web server
    timeout /t 2 /nobreak > NUL
)

echo [2/2] Opening Chrome to %URL%...
start chrome "%URL%"

:: Optional: closes the window automatically after 3 seconds
timeout /t 3
exit