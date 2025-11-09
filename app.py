from flask import Flask, request, jsonify
from get_github_user import collect_profile_from_github_url
from get_linkedin_user import collect_linkedin_profile

app = Flask(__name__)

@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "message": "Profile Collector API. POST /github or /linkedin with JSON { 'url': '...' }"
    })

@app.route("/github", methods=["POST"])
def github_endpoint():
    try:
        payload = request.get_json(force=True)
        url = payload.get("url")
        if not url:
            return jsonify({"error": "Missing 'url' field"}), 400
        profile = collect_profile_from_github_url(url)
        return jsonify(profile)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/linkedin", methods=["POST"])
def linkedin_endpoint():
    try:
        payload = request.get_json(force=True)
        url = payload.get("url")
        if not url:
            return jsonify({"error": "Missing 'url' field"}), 400
        profile = collect_linkedin_profile(url)
        return jsonify(profile)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
