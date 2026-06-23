# NESPAK Project Monitoring System - Desktop Edition

## Complete Internal PC Software (No Browser Required)

This is a complete desktop application that runs entirely on your Windows PC without needing a web browser.

## Features

✅ **All Original Web Features Preserved**
- Dashboard with KPIs and charts
- Project Management
- Invoice/Billing Entry
- Receipt Tracking  
- Expense Management
- Cheque Management
- Sales Tax Performa
- Reports
- Settings

✅ **Desktop Advantages**
- No browser needed - runs as native Windows app
- Works offline - no internet required
- All data stored locally in SQLite database
- Error messages displayed in-app
- Auto-starts local server

## Installation on Windows

### Option 1: Run Directly (Recommended for Testing)

1. Install Python 3.8 or newer from https://python.org
2. During installation, check "Add Python to PATH"
3. Open Command Prompt in the software folder
4. Run these commands:

```bash
pip install flask openpyxl pywebview
```

5. Double-click `START_DESKTOP.bat` or run:
```bash
python desktop_app.py
```

### Option 2: Build Standalone EXE (For Distribution)

1. First install dependencies:
```bash
pip install flask openpyxl pyinstaller
```

2. Build the executable:
```bash
pyinstaller --onefile --windowed --name "NESPAK_PMS" --add-data "templates;templates" --add-data "static;static" --add-data "nespak_pms.db;." desktop_app.py
```

3. Find your EXE in the `dist` folder
4. Copy `NESPAK_PMS.exe` to your desired location
5. Double-click to run!

## Login Credentials

- **Admin Password:** admin123
- **Guest Password:** guest123

## Data Storage

All your data is stored in `nespak_pms.db` file in the same folder. This is a SQLite database that contains:
- Projects
- Transactions (Invoices, Receipts, Expenses)
- Cheques
- Performas
- Settings
- Edit Logs

**Backup regularly by copying this file!**

## Error Handling

The software now includes comprehensive error handling:
- Any errors are caught and displayed in the application
- Error messages show what went wrong
- Traceback information available for debugging
- Database integrity checks on startup

## Troubleshooting

### Application won't start
1. Make sure Python is installed
2. Run: `pip install flask openpyxl pywebview`
3. Check if any antivirus is blocking the app

### Database errors
1. Close the application
2. Make a backup of `nespak_pms.db`
3. Try restarting the application

### Missing templates/static files
Make sure you're running from the correct directory where all files are located.

## Support

For issues, check the error message displayed in the application and refer to the traceback for details.

---
**Version:** 3.0 Desktop Edition
**Built for:** NESPAK Construction Management Division
