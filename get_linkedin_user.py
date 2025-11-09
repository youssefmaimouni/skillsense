# get_linkedin_user.py
import os
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()   

# ---------------- Configuration ----------------
SCRAPETABLE_API_KEY = os.getenv("SCRAPETABLE_API_KEY")

SCRAPETABLE_API_URL = "https://v3.scrapetable.com/linkedin/people"


def collect_linkedin_profile(profile_url: str):
    """
    Fetch LinkedIn profile data using Scrapetable API and return it as a structured dict.
    :param profile_url: LinkedIn profile URL (e.g. https://www.linkedin.com/in/username/)
    :return: dict containing parsed LinkedIn profile data
    """
    if not profile_url or "linkedin.com/in/" not in profile_url:
        raise ValueError("Invalid or missing LinkedIn profile URL")

    params = {
        "key": SCRAPETABLE_API_KEY,
        "profileUrl": profile_url
    }

    headers = {"Content-Type": "application/json"}

    # Make API call
    response = requests.get(SCRAPETABLE_API_URL, params=params, headers=headers, timeout=30)

    if response.status_code != 200:
        raise Exception(f"Scrapetable API request failed ({response.status_code}): {response.text}")

    data = response.json()

    if not data.get("success"):
        raise Exception(f"Scrapetable API error: {data}")

    person = data.get("person", {})

    profile = {
        "platform": "linkedin",
        "fullName": person.get("fullName"),
        "headline": person.get("headline"),
        "summary": person.get("summary"),
        "location": person.get("geoFull"),
        "skills": person.get("skills", []),
        "education": person.get("education", []),
        "projects": person.get("projects", []),
        "positions": person.get("positions", []),
        "profileUrl": person.get("profileUrl") or profile_url,
        "profilePicture": person.get("profilePicture"),
        "raw_data": person,
    }

    return profile


# ---------------- Example standalone usage ----------------
if __name__ == "__main__":
    test_url = "https://www.linkedin.com/in/maimouni-youssef/"
    result = collect_linkedin_profile(test_url)
    import json
    with open("linkedin_profile_data.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=4, ensure_ascii=False)
    print("✅ LinkedIn profile data saved to linkedin_profile_data.json")
