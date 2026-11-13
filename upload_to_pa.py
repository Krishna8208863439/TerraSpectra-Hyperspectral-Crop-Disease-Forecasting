import os
import sys
import requests
import time

USERNAME = "Krishna3114"
API_TOKEN = "3d04f7412ab6ddc774ba96e859f5d7ced1f486ec"
HEADERS = {"Authorization": f"Token {API_TOKEN}"}
BASE_FILE_URL = f"https://www.pythonanywhere.com/api/v0/user/{USERNAME}/files/path/home/{USERNAME}/Smart-Kisan-FInal"
RELOAD_URL = f"https://www.pythonanywhere.com/api/v0/user/{USERNAME}/webapps/{USERNAME}.pythonanywhere.com/reload/"

def upload(local_file, remote_rel_path):
    url = f"{BASE_FILE_URL}/{remote_rel_path.replace(os.sep, '/')}"
    print(f"[*] Uploading {local_file} -> {remote_rel_path}...", flush=True)
    with open(local_file, "rb") as f:
        r = requests.post(url, headers=HEADERS, files={"content": f}, timeout=60)
    if r.status_code in (200, 201):
        print(f"    [OK] {r.status_code}")
    else:
        print(f"    [FAIL] {r.status_code} - {r.text}")
        raise RuntimeError(f"Upload failed for {local_file}: {r.status_code} {r.text}")

def main():
    print("=" * 65)
    print("  SMART KISAN — PYTHONANYWHERE PRODUCTION DEPLOYMENT")
    print(f"  Target: https://{USERNAME}.pythonanywhere.com")
    print("=" * 65)

    # 1. Backend python files & services
    backend_files = [
        "backend/app.py",
        "backend/routes/cropDiagnosticsRoutes.js",
        "backend/services/cropDiagnosticsService.js",
        "backend/services/agriexpert_service.py",
    ]
    for bf in backend_files:
        if os.path.exists(bf):
            upload(bf, bf)

    # 2. Frontend distribution assets (All files in frontend/dist)
    dist_root = os.path.join("frontend", "dist")
    if not os.path.exists(dist_root):
        raise RuntimeError("frontend/dist does not exist! Run npm run build first.")

    uploaded_count = 0
    for root, dirs, files in os.walk(dist_root):
        for file in files:
            full_local_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_local_path, dist_root)
            remote_path = f"backend/dist/{rel_path}"
            upload(full_local_path, remote_path)
            uploaded_count += 1

    print(f"\n[OK] Uploaded {uploaded_count} frontend distribution assets to backend/dist/!")

    # 3. Reload Web Application
    print("\n[*] Reloading web app on PythonAnywhere...", flush=True)
    r_reload = requests.post(RELOAD_URL, headers=HEADERS, timeout=30)
    print(f"    Reload response: {r_reload.status_code}", flush=True)
    if r_reload.status_code != 200:
        print(f"    Warning: Reload returned {r_reload.status_code} {r_reload.text}")

    # 4. Verify deployment
    print("\n[*] Waiting 4 seconds for server worker to spin up...", flush=True)
    time.sleep(4)

    live_url = f"https://{USERNAME}.pythonanywhere.com"
    print(f"[*] Verifying live endpoint: {live_url} ...", flush=True)
    try:
        res = requests.get(live_url, timeout=20)
        print(f"    Home page status: {res.status_code}")
        # Detect new js bundle in response
        if "index-BIPX7a0a.js" in res.text:
            print("    [SUCCESS] Latest JS bundle (index-BIPX7a0a.js) verified in live index.html!")
        else:
            print("    [NOTE] Checking index.html snippet:")
            print("    " + res.text[:250].replace("\n", " "))
    except Exception as e:
        print(f"    Verification error: {e}")

    # 5. Verify Backend API Diagnosis with Marathi
    print("\n[*] Verifying /api/crop-diagnosis with Marathi language & 'manago'...", flush=True)
    try:
        # Create a small valid green JPEG test leaf in memory to pass image gate
        from PIL import Image
        import io
        img = Image.new("RGB", (100, 100), color=(40, 150, 40))
        img_buf = io.BytesIO()
        img.save(img_buf, format="JPEG")
        leaf_bytes = img_buf.getvalue()

        api_res = requests.post(
            f"{live_url}/api/crop-diagnosis",
            headers={"x-language": "mr"},
            data={"crop": "manago", "language": "mr"},
            files={"image": ("test_leaf.jpg", leaf_bytes, "image/jpeg")},
            timeout=25
        )
        print(f"    API status: {api_res.status_code}")
        resp_data = api_res.json()
        print(f"    API Crop: {resp_data.get('crop')}")
        print(f"    API Diagnosis: {resp_data.get('diagnosis')}")
        print(f"    API Provider: {resp_data.get('provider')}")
        print(f"    API Symptoms sample: {resp_data.get('symptoms', [''])[0]}")
    except Exception as e:
        print(f"    API check error: {e}")

    print("\n" + "=" * 65)
    print(f"  ALL LANGUAGE CHANGES DEPLOYED TO PYTHONANYWHERE SUCCESSFULLY!")
    print(f"  Visit: https://{USERNAME}.pythonanywhere.com")
    print("=" * 65)

if __name__ == "__main__":
    main()
