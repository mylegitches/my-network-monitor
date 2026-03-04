@echo off
setlocal enabledelayedexpansion

set LOG=network_diagnostic_log.txt
set ROUTER=192.168.1.1
set INTERNET=8.8.8.8
set DNS=google.com

echo Network Diagnostic Started > %LOG%
echo ================================= >> %LOG%

:loop

echo. >> %LOG%
echo -------------------------------------------------- >> %LOG%
echo %date% %time% >> %LOG%

echo Checking Router... >> %LOG%
ping -n 1 %ROUTER% | find "TTL=" >nul
if errorlevel 1 (
    echo ROUTER FAIL >> %LOG%
) else (
    echo ROUTER OK >> %LOG%
)

echo Checking Internet IP... >> %LOG%
ping -n 1 %INTERNET% | find "TTL=" >nul
if errorlevel 1 (
    echo INTERNET FAIL >> %LOG%
) else (
    echo INTERNET OK >> %LOG%
)

echo Checking DNS resolution... >> %LOG%
nslookup %DNS% >nul 2>&1
if errorlevel 1 (
    echo DNS FAIL >> %LOG%
) else (
    echo DNS OK >> %LOG%
)

echo Running traceroute snapshot... >> %LOG%
tracert -d -h 5 %INTERNET% >> %LOG%

timeout /t 10 >nul
goto loop