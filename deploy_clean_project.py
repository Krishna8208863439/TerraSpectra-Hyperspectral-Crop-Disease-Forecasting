import os
import sys
import time
import requests

USERNAME = "Krishna3114"
API_TOKEN = "3d04f7412ab6ddc774ba96e859f5d7ced1f486ec"
HOST = "www.pythonanywhere.com"
HEADERS = {"Authorization": f"Token {API_TOKEN}"}
BASE_URL = f"https://{HOST}/api/v0/user/{USERNAME}"

def log(msg):
    print(f"[*] {msg}", flush=True)

def upload_file(local_path, remote_path):
    log(f"Uploading {os.path.basename(local_path)} ({os.path.getsize(local_path)} bytes) to {remote_path}...")
    url = f"{BASE_URL}/files/path/home/{USERNAME}/{remote_path}"
    with open(local_path, "rb") as f:
        r = requests.post(url, headers=HEADERS, files={"content": f})
    log(f"Upload status: {r.status_code}")
    if r.status_code not in (200, 201):
        raise RuntimeError(f"Upload failed: {r.text}")

def write_remote_file(remote_path, content):
    log(f"Writing remote file {remote_path}...")
    url = f"{BASE_URL}/files/path{remote_path}"
    r = requests.post(url, headers=HEADERS, files={"content": content.encode("utf-8")})
    log(f"Write status: {r.status_code}")
    if r.status_code not in (200, 201):
        raise RuntimeError(f"Write failed: {r.text}")

def read_remote_file(remote_path):
    url = f"{BASE_URL}/files/path{remote_path}"
    r = requests.get(url, headers=HEADERS)
    if r.status_code == 200:
        return r.text
    return None

def reload_webapp():
    log(f"Reloading webapp {USERNAME}.pythonanywhere.com...")
    url = f"{BASE_URL}/webapps/{USERNAME}.pythonanywhere.com/reload/"
    r = requests.post(url, headers=HEADERS)
    log(f"Reload response: {r.status_code}")
    if r.status_code != 200:
        raise RuntimeError(f"Reload failed: {r.text}")

def main():
    log("=" * 60)
    log("  SMART KISAN - COMPLETE PYTHONANYWHERE REPLACEMENT DEPLOYMENT")
    log("=" * 60)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    zip_path = os.path.join(script_dir, "smart_kisan_deploy.zip")

    if not os.path.exists(zip_path):
        raise RuntimeError("smart_kisan_deploy.zip not found!")

    # Step 1: Upload the clean zip bundle
    upload_file(zip_path, "smart_kisan_deploy.zip")

    # Step 2: Install migration & extraction WSGI
    migration_wsgi = f"""import os
import sys
import shutil
import zipfile
import traceback

log_lines = []
def wlog(msg):
    log_lines.append(msg)

wlog("=== DEPLOYMENT EXECUTION STARTED ===")
home = "/home/{USERNAME}"

# Folders to delete completely
old_folders = [
    os.path.join(home, "Smart-Kisan-FInal"),
    os.path.join(home, "smart-kisan"),
    os.path.join(home, "smart-kisan-backend"),
    os.path.join(home, "smart-kisan-backend-python"),
    os.path.join(home, "smart-kisan-frontend"),
    os.path.join(home, ".cache"),
]

for folder in old_folders:
    if os.path.exists(folder):
        wlog(f"Removing old folder: {{folder}}")
        try:
            shutil.rmtree(folder, ignore_errors=True)
            wlog(f"Removed: {{folder}}")
        except Exception as e:
            wlog(f"Error removing {{folder}}: {{e}}")

# Files to delete
old_files = [
    "backend.zip", "dist.zip", "active_ports.txt",
    "py_stdout.log", "py_stderr.log", "wsgi_debug.log", "package-lock.json"
]
for f in old_files:
    fp = os.path.join(home, f)
    if os.path.exists(fp):
        try:
            os.remove(fp)
            wlog(f"Deleted old file: {{f}}")
        except Exception as e:
            wlog(f"Error removing {{f}}: {{e}}")

# Unpack new deployment
zip_file = os.path.join(home, "smart_kisan_deploy.zip")
if os.path.exists(zip_file):
    wlog(f"Extracting {{zip_file}} to {{home}}...")
    try:
        with zipfile.ZipFile(zip_file, 'r') as zf:
            zf.extractall(home)
        wlog("Extraction successful!")
        os.remove(zip_file)
        wlog("Deleted uploaded zip bundle.")
    except Exception as e:
        wlog(f"Extraction error: {{e}}")
else:
    wlog("Error: smart_kisan_deploy.zip not found!")

# Write deployment log
status_log_path = os.path.join(home, "deploy_status.log")
with open(status_log_path, "w") as f:
    f.write("\\n".join(log_lines) + "\\n")

# Load application
project_home = os.path.join(home, "Smart-Kisan-FInal", "backend")
if project_home not in sys.path:
    sys.path.insert(0, project_home)

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(project_home, ".env"))
    from app import app as application
except Exception as e:
    with open(status_log_path, "a") as f:
        f.write(f"App load error: {{traceback.format_exc()}}\\n")
    raise
"""

    wsgi_remote_path = f"/var/www/{USERNAME}_pythonanywhere_com_wsgi.py"
    write_remote_file(wsgi_remote_path, migration_wsgi)

    # Step 3: Reload webapp to activate migration
    reload_webapp()

    # Step 4: Trigger web request to fire WSGI
    log("Sending trigger request to execute migration...")
    time.sleep(2)
    try:
        res = requests.get(f"https://{USERNAME}.pythonanywhere.com/", timeout=30)
        log(f"Trigger request response status: {res.status_code}")
    except Exception as e:
        log(f"Trigger request note: {e}")

    # Step 5: Check deployment log
    time.sleep(3)
    status_log = read_remote_file(f"/home/{USERNAME}/deploy_status.log")
    log("Deployment log from PythonAnywhere:")
    if status_log:
        for line in status_log.splitlines():
            log(f"  PA: {line}")
    else:
        log("No status log found yet, retrying in 5 seconds...")
        time.sleep(5)
        status_log = read_remote_file(f"/home/{USERNAME}/deploy_status.log")
        if status_log:
            for line in status_log.splitlines():
                log(f"  PA: {line}")

    # Step 6: Install clean permanent WSGI configuration
    log("Setting permanent production WSGI configuration...")
    clean_wsgi = f"""import os
import sys

# Path to Smart Kisan Flask backend
project_home = '/home/{USERNAME}/Smart-Kisan-FInal/backend'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Load environment variables from .env
from dotenv import load_dotenv
load_dotenv(os.path.join(project_home, '.env'))

# Import Flask app entry point
from app import app as application
"""
    write_remote_file(wsgi_remote_path, clean_wsgi)
    reload_webapp()
    time.sleep(3)

    # Step 7: Verify live application
    log("Verifying live deployment...")
    live_url = f"https://{USERNAME}.pythonanywhere.com"
    res_home = requests.get(live_url, timeout=15)
    log(f"Home page HTTP status: {res_home.status_code}")
    log(f"Home page preview: {res_home.text[:150]}...")

    res_api = requests.get(f"{live_url}/api/health", timeout=15)
    log(f"API Health HTTP status: {res_api.status_code}")
    log(f"API Health response: {res_api.text}")

    res_market = requests.get(f"{live_url}/api/market", timeout=15)
    log(f"Market API HTTP status: {res_market.status_code}")

    if res_home.status_code == 200 and res_api.status_code == 200:
        log("=" * 60)
        log("🎉 DEPLOYMENT SUCCEEDED!")
        log(f"🌐 Live URL: {live_url}")
        log("=" * 60)
    else:
        log(f"⚠️ Warning: Check response codes above (Home: {res_home.status_code}, API: {res_api.status_code})")

if __name__ == "__main__":
    main()
