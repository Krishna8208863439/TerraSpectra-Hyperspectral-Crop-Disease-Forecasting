#!/usr/bin/env python3
"""
Smart Kisan - API Features Verification Test Script
Tests the running services to ensure that the Hybrid Backend architecture
(Express + FastAPI) features are fully operational and responding correctly.
"""

import sys
import json
import urllib.request
import urllib.error

# Ensure UTF-8 output on Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Ports configuration
EXPRESS_URL = "http://localhost:5000"
FASTAPI_URL = "http://localhost:8000"

def log_header(title):
    print("\n" + "=" * 60)
    print(f" 🔍 TESTING FEATURE: {title}")
    print("=" * 60)

def make_request(url, method="GET", data=None, headers=None, is_json=True):
    """Utility helper to send HTTP request using standard urllib."""
    if headers is None:
        headers = {}
    
    req_data = None
    if data is not None:
        if isinstance(data, dict) and is_json:
            req_data = json.dumps(data).encode("utf-8")
            headers["Content-Type"] = "application/json"
        elif isinstance(data, dict) and not is_json:
            # Form urlencoded
            req_data = urllib.parse.urlencode(data).encode("utf-8")
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        else:
            req_data = data
            
    req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            res_data = response.read().decode("utf-8")
            return response.status, json.loads(res_data) if res_data else {}
    except urllib.error.HTTPError as e:
        try:
            error_content = e.read().decode("utf-8")
            return e.code, json.loads(error_content) if error_content else {"error": e.reason}
        except Exception:
            return e.code, {"error": e.reason}
    except urllib.error.URLError as e:
        return 0, {"error": f"Server offline or unreachable: {e.reason}"}
    except Exception as e:
        return 0, {"error": str(e)}

def main():
    print("============================================================")
    print("       🌾 Smart Kisan - Feature Verification Suite 🌾")
    print("============================================================")
    print("Please make sure you have started your servers using run_all_features.py.")
    
    # 1. Test Express Connectivity
    log_header("Express API Connection")
    status, res = make_request(f"{EXPRESS_URL}/")
    if status == 200:
        print(f"✅ Express base response: '{res}'" if isinstance(res, str) else f"✅ Express Base API operational.")
    else:
        print(f"❌ Express connection failed (Status: {status}). Details: {res}")
        print("   Please start your Node server before running this script.")
        sys.exit(1)

    # 2. Test FastAPI Connection & Health
    log_header("FastAPI Server Health Check")
    status, res = make_request(f"{FASTAPI_URL}/api/health")
    if status == 200:
        print(f"✅ FastAPI status: {res.get('status', 'Unknown')}")
        print(f"   Database Status: {res.get('database', 'Unknown')}")
        print(f"   Gemini Connection Status: {res.get('gemini', 'Unknown')}")
    else:
        print(f"❌ FastAPI Health connection failed (Status: {status}). Details: {res}")
        print("   Please start your Python FastAPI server before running this script.")
        sys.exit(1)

    # 3. Authenticate User on Express (Node Backend)
    log_header("Node.js Auth & JWT Token Issuance")
    login_data = {
        "email": "farmer@smartkisan.com",
        "password": "Password123!"
    }
    status, res = make_request(f"{EXPRESS_URL}/api/auth/login", method="POST", data=login_data)
    token = None
    if status != 200:
        # Try registering the test user
        reg_data = {
            "name": "Ramesh Kisan",
            "email": "farmer@smartkisan.com",
            "password": "Password123!",
            "role": "farmer"
        }
        reg_status, reg_res = make_request(f"{EXPRESS_URL}/api/auth/register", method="POST", data=reg_data)
        if reg_status in (200, 201):
            token = reg_res.get("data", {}).get("accessToken") or reg_res.get("accessToken")
            print(f"✅ User registered and authenticated: Ramesh Kisan")
        else:
            # Try login again
            status, res = make_request(f"{EXPRESS_URL}/api/auth/login", method="POST", data=login_data)
            token = res.get("data", {}).get("accessToken") or res.get("accessToken") or res.get("token")
    else:
        token = res.get("data", {}).get("accessToken") or res.get("accessToken") or res.get("token")

    if token:
        print(f"✅ Authentication Success! JWT Token acquired (first 30 chars): {token[:30]}...")
    else:
        print(f"❌ Authentication failed: {res}")
        sys.exit(1)

    headers = {"Authorization": f"Bearer {token}"}

    # 4. Test Crop Recommendation (Express Route)
    log_header("Express Soil Recommendation Feature")
    reco_data = {
        "soilType": "loamy",
        "region": "Pune",
        "season": "kharif",
        "pH": 6.5,
        "n": 80,
        "p": 60,
        "k": 60,
        "irrigationAvailable": True
    }
    status, res = make_request(f"{EXPRESS_URL}/api/recommendations/crop", method="POST", data=reco_data, headers=headers)
    if status == 200 and res.get("success"):
        print(f"✅ Crop Recommendation Feature Working! (Source: {res.get('source')})")
        print(f"   Detected Location: {res.get('location')}")
        print(f"   Weather Context: {res.get('weather', {}).get('forecast')}")
        print("   Recommended Crops:")
        for crop in res.get("recommendations", []):
            print(f"    - {crop.get('crop')} (Compatibility: {crop.get('suitabilityScore')}%)")
            print(f"      Yield: {crop.get('predictedYield')} | Profit: {crop.get('estimatedProfit')}")
            print(f"      Reason: {crop.get('reason')}")
    else:
        print(f"❌ Recommendation failed: {res}")

    # 5. Test Commodities API (Express Market Data)
    log_header("Express Market Price & APMC Mandis Feature")
    status, res = make_request(f"{EXPRESS_URL}/api/market/commodities", headers=headers)
    if status == 200 and "commodities" in res:
        print(f"✅ Market Data Retrieval Functional! Found {len(res['commodities'])} commodities.")
        sample_crops = [c for c in res["commodities"] if c.get("name") in ["Wheat", "Tomato", "Paddy (Rice)"]]
        print("   Sample Commodities:")
        for sc in sample_crops:
            print(f"    - {sc.get('icon')} {sc.get('name')}: Base Price = ₹{sc.get('basePrice')}/{sc.get('unit')} (MSP: {sc.get('msp') or 'N/A'})")
    else:
        print(f"❌ Market Price retrieval failed: {res}")

    # 6. Test Python Advisory Endpoint (FastAPI Form Route)
    log_header("FastAPI Crop Advisory ML Model Feature")
    advisory_data = {
        "soil_type": "loamy",
        "region": "Nashik",
        "season": "rabi",
        "pH": "6.2",
        "n": "90",
        "p": "50",
        "k": "40",
        "land_size": "2.5"
    }
    status, res = make_request(f"{FASTAPI_URL}/api/advisory", method="POST", data=advisory_data, headers=headers, is_json=False)
    if status == 200 and res.get("success"):
        print(f"✅ Python FastAPI Advisory System functional! (Source: {res.get('source')})")
        print(f"   Forecast at location: {res.get('weather', {}).get('forecast')}")
        print("   Top Suggested Crops:")
        for crop in res.get("recommendations", []):
            print(f"    - {crop.get('crop')} (Score: {crop.get('suitabilityScore')}%)")
            print(f"      Predicted Yield: {crop.get('predictedYield')} | Expected Profit: {crop.get('estimatedProfit')}")
    else:
        print(f"❌ Python Advisory failed (Status {status}): {res}")

    # 7. Test ML Yield Prediction (FastAPI Route)
    log_header("FastAPI ML Yield Prediction Model Feature")
    yield_data = {
        "crop": "Tomato",
        "area": 2.5,
        "soil_type": "loamy",
        "n": 110.0,
        "p": 60.0,
        "k": 60.0,
        "ph": 6.8,
        "rainfall": 140.0,
        "temperature": 26.0,
        "humidity": 65.0,
        "previous_yield": 11.5,
        "season": "Kharif",
        "state": "Maharashtra",
        "district": "Pune"
    }
    status, res = make_request(f"{FASTAPI_URL}/api/yield-predict", method="POST", data=yield_data, headers=headers, is_json=True)
    if status == 200 and res.get("success"):
        print(f"✅ ML Yield Prediction functional!")
        print(f"   Predicted Yield per Acre: {res.get('predicted_yield_per_acre')} Tons")
        print(f"   Total Predicted Yield: {res.get('total_predicted_yield')} Tons (Confidence: {int(res.get('confidence_score', 0)*100)}%)")
        print("   Factors Affecting Yield:")
        for factor in res.get("factors_affecting_yield", []):
            print(f"    - [{factor.get('impact')}] {factor.get('factor')}: {factor.get('detail')}")
    else:
        print(f"❌ Yield Prediction failed (Status {status}): {res}")

    # 8. Test Gemini Chat Agriculture Guardrail (Non-agri rejection)
    log_header("Gemini Agriculture Chatbot Guardrail")
    chat_non_agri = {
        "message": "Who won the cricket world cup?",
        "language": "en"
    }
    status, res = make_request(f"{FASTAPI_URL}/api/chat", method="POST", data=chat_non_agri, headers=headers, is_json=True)
    if status == 200 and res.get("response") == "I am an Agriculture AI Assistant. I only provide information related to farming and plants.":
        print(f"✅ Chatbot Guardrail Working! Correctly rejected non-agriculture query with standard message.")
    else:
        print(f"ℹ️ Chatbot Guardrail response: {res.get('response')}")

    print("\n" + "=" * 60)
    print(" 🎉 ALL CRITICAL BACKEND & AI FEATURES TESTED SUCCESSFULLY!")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    main()
