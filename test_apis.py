# test_apis.py
import requests
import json

# ---------- Configuration ----------
FLASK_BASE_URL = "http://127.0.0.1:5000"

GITHUB_PROFILE = "https://github.com/youssefmaimouni"
LINKEDIN_PROFILE = "https://www.linkedin.com/in/maimouni-youssef/"

# ---------- Helper function ----------
def test_endpoint(endpoint, url, output_file):
    try:
        response = requests.post(f"{FLASK_BASE_URL}/{endpoint}", json={"url": url})
        data = response.json()
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"✅ {endpoint} data saved to {output_file}")
    except Exception as e:
        print(f"❌ Error testing {endpoint}: {e}")

# ---------- Run tests ----------
test_endpoint("github", GITHUB_PROFILE, "github_profile.json")
test_endpoint("linkedin", LINKEDIN_PROFILE, "linkedin_profile.json")
