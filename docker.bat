@echo off
setlocal

set CMD=%1
if "%CMD%"=="" set CMD=dev-up

if "%CMD%"=="dev-up" goto dev_up
if "%CMD%"=="dev-build" goto dev_build
if "%CMD%"=="dev-down" goto dev_down
if "%CMD%"=="dev-logs" goto dev_logs
if "%CMD%"=="prod-up" goto prod_up
if "%CMD%"=="prod-build" goto prod_build
if "%CMD%"=="prod-down" goto prod_down
if "%CMD%"=="prod-logs" goto prod_logs

echo Unknown command: %CMD%
echo.
echo Supported commands:
echo   dev-up
echo   dev-build
echo   dev-down
echo   dev-logs
echo   prod-up
echo   prod-build
echo   prod-down
echo   prod-logs
exit /b 1

:dev_up
docker compose up
goto end

:dev_build
docker compose up --build
goto end

:dev_down
docker compose down
goto end

:dev_logs
docker compose logs -f
goto end

:prod_up
docker compose -f docker-compose.prod.yml up -d
goto end

:prod_build
docker compose -f docker-compose.prod.yml up --build -d
goto end

:prod_down
docker compose -f docker-compose.prod.yml down
goto end

:prod_logs
docker compose -f docker-compose.prod.yml logs -f
goto end

:end
endlocal
