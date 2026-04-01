@echo off
echo ============================================================
echo   ShopKart — Database Reset Tool
echo ============================================================
echo.

set FOLDER=%~dp0

if exist "%FOLDER%shopkart.db" (
    echo  Purani database mili: shopkart.db
    del "%FOLDER%shopkart.db"
    echo  ✅ Database delete ho gayi!
) else (
    echo  Database pehle se nahi hai — kuch karne ki zaroorat nahi.
)

echo.
echo  Ab server start karo:  python start.py
echo.
pause
