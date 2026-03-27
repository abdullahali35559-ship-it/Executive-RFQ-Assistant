@echo off
chcp 65001 > nul
echo ======================================================================
echo OUTLOOK CONNECTION TEST
echo ======================================================================
echo.

cd /d "D:\RFQ agent"
call venv\Scripts\activate.bat

echo Testing Outlook connection...
echo.
echo Current settings:
echo   Email: aimicrossrlsoft@outlook.com
echo   Host: outlook.office365.com
echo   Port: 993
echo   App Password: inus...yhru
echo.

python -c "import sys; sys.path.append('.'); from imapclient import IMAPClient; import ssl; ctx = ssl.create_default_context(); c = IMAPClient('outlook.office365.com', 993, ssl_context=ctx); c.login('aimicrossrlsoft@outlook.com', 'inuspowjodyvyhru'); print('SUCCESS: Connected!'); c.logout()" 2>&1

if errorlevel 1 (
    echo.
    echo ======================================================================
    echo FAILED: App password does not work
    echo ======================================================================
    echo.
    echo REASON: Microsoft personal accounts do not support app passwords for IMAP
    echo.
    echo SOLUTIONS:
    echo.
    echo 1. Use regular password ONLY if 2FA is disabled
    echo    - Go to: https://account.microsoft.com/security  
    echo    - Turn OFF: Two-step verification
    echo    - Use your login password instead
    echo.
    echo 2. Use Gmail instead (RECOMMENDED - already working^)
    echo    - Edit .env
    echo    - Set: EMAIL_PROVIDER=gmail
    echo.
    echo 3. Get Office 365 business account
    echo    - Enterprise accounts support app passwords
    echo.
) else (
    echo.
    echo ======================================================================
    echo SUCCESS! Outlook is connected
    echo ======================================================================
)

pause
