"""
run.py — Launch NESPAK PMS Web Server
Double-click this file OR run:  python run.py

After starting, open your browser to:
  http://localhost:5000
"""
import sys, os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

if sys.version_info < (3, 8):
    print("ERROR: Python 3.8 or newer required.")
    input("Press Enter to exit.")
    sys.exit(1)

missing = []
try: import flask
except ImportError: missing.append("flask")
try: import openpyxl
except ImportError: missing.append("openpyxl")

if missing:
    print("Missing required packages:", ", ".join(missing))
    print(f"\nRun this command:\n  pip install {' '.join(missing)}\n")
    input("Press Enter to exit.")
    sys.exit(1)

from app import app, init_db
import socket

init_db()
hostname = socket.gethostname()
try:
    local_ip = socket.gethostbyname(hostname)
except:
    local_ip = "127.0.0.1"

print("\n" + "="*60)
print("  NESPAK Project Monitoring System")
print("="*60)
print(f"  This computer:  http://localhost:5000")
print(f"  Other computer: http://{local_ip}:5000")
print("\n  Login:")
print("    Admin password: admin123")
print("    Guest password: guest123")
print("\n  Keep this window open while using the system.")
print("  Press Ctrl+C to stop the server.")
print("="*60 + "\n")

app.run(host="0.0.0.0", port=5000, debug=False)
