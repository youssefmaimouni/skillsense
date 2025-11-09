import os
import uuid
from threading import Thread
from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# --- Import des extracteurs ---
from cv_extractor import extract_cv_data
from github_extractor.api_client import get_profile_from_github_url
from linkedin_extractor.scraper import collect_profile_from_linkedin_url
from get_github_user import collect_profile_from_github_url as simple_github
from get_linkedin_user import collect_linkedin_profile as simple_linkedin

# ======================================================================
# --- CONFIGURATION DE L’APPLICATION ---
# ======================================================================

app = Flask(__name__)

# Base de données
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# Uploads
UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"pdf", "docx"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Jobs en mémoire
JOBS = {}

# ======================================================================
# --- MODÈLE DE BASE DE DONNÉES ---
# ======================================================================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)


with app.app_context():
    db.create_all()


# ======================================================================
# --- UTILITAIRES ---
# ======================================================================
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def run_extraction_task(job_id, extractor_func, **kwargs):
    """
    Exécute une tâche d’extraction en arrière-plan
    """
    print(f"[INFO] Démarrage du job {job_id}")
    try:
        result_pydantic = extractor_func(**kwargs)
        result_dict = result_pydantic.model_dump()
        JOBS[job_id] = {"status": "completed", "result": result_dict}
        print(f"[INFO] Job {job_id} terminé avec succès")
    except Exception as e:
        print(f"[ERREUR] Job {job_id}: {e}")
        JOBS[job_id] = {"status": "error", "message": str(e)}


# ======================================================================
# --- ROUTES HTML FRONTEND ---
# ======================================================================

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/ui")
def ui():
    return render_template("index.html")

@app.route("/profiles")
def profiles():
    return render_template("profiles.html")


# ======================================================================
# --- ROUTES UTILISATEUR (Signup / Login / Update) ---
# ======================================================================

@app.route("/signup", methods=["POST"])
def signup():
    data = request.get_json(force=True)
    name = data.get("name")
    email = data.get("email")
    password = data.get("password")

    if not all([name, email, password]):
        return jsonify({"error": "Missing fields"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "User already exists"}), 400

    hashed_password = generate_password_hash(password)
    user = User(name=name, email=email, password_hash=hashed_password)
    db.session.add(user)
    db.session.commit()

    return jsonify({"message": "User registered successfully", "user_id": user.id})


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json(force=True)
    email = data.get("email")
    password = data.get("password")

    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({"error": "Invalid email or password"}), 401

    return jsonify({"message": "Login successful", "user_id": user.id})


@app.route("/update_profile", methods=["PUT"])
def update_profile():
    data = request.get_json(force=True)
    user_id = data.get("user_id")
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    user.name = data.get("name", user.name)
    user.email = data.get("email", user.email)
    db.session.commit()

    return jsonify({
        "message": "Profile updated",
        "user": {"id": user.id, "name": user.name, "email": user.email}
    })


# ======================================================================
# --- ROUTES D’EXTRACTION DIRECTE (GitHub / LinkedIn) ---
# ======================================================================

@app.route("/github", methods=["POST"])
def github_endpoint():
    try:
        payload = request.get_json(force=True)
        url = payload.get("url")
        if not url:
            return jsonify({"error": "Missing 'url' field"}), 400
        profile = simple_github(url)
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
        profile = simple_linkedin(url)
        return jsonify(profile)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# ======================================================================
# --- ROUTES D’EXTRACTION ASYNCHRONE (CV / GitHub / LinkedIn) ---
# ======================================================================

@app.route("/extract", methods=["POST"])
def start_extraction():
    """
    Lancer un job d’extraction asynchrone (cv / linkedin / github)
    """
    source_type = request.form.get("source_type")
    if not source_type:
        return jsonify({"error": "Missing 'source_type' (must be 'cv', 'linkedin', or 'github')"}), 400

    job_id = str(uuid.uuid4())
    extractor_func = None
    kwargs = {}

    # Sélection du bon extracteur
    if source_type == "cv":
        if "file" not in request.files:
            return jsonify({"error": "No file provided"}), 400
        file = request.files["file"]
        if file.filename == "" or not allowed_file(file.filename):
            return jsonify({"error": "Invalid or missing file"}), 400

        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)
        extractor_func = extract_cv_data
        kwargs = {"file_path": filepath}

    elif source_type == "linkedin":
        url = request.form.get("url")
        if not url:
            return jsonify({"error": "Missing 'url' for linkedin"}), 400
        extractor_func = collect_profile_from_linkedin_url
        kwargs = {"url": url}

    elif source_type == "github":
        url = request.form.get("url")
        if not url:
            return jsonify({"error": "Missing 'url' for github"}), 400
        extractor_func = get_profile_from_github_url
        kwargs = {"url": url}
    else:
        return jsonify({"error": f"Invalid source_type: '{source_type}'"}), 400

    # Lancement du thread
    JOBS[job_id] = {"status": "pending"}
    thread = Thread(target=run_extraction_task, args=(job_id, extractor_func), kwargs=kwargs)
    thread.start()

    return jsonify({"message": f"{source_type.capitalize()} processing started.", "job_id": job_id}), 202


# ======================================================================
# --- ROUTE DIRECTE POUR CV UPLOAD (compatible avec frontend /profiles) ---
# ======================================================================

@app.route("/cv", methods=["POST"])
def cv_endpoint():
    """
    Route pour recevoir un CV et renvoyer directement les résultats de l'extraction.
    """
    if "file" not in request.files:
        return jsonify({"error": "No file part in request"}), 400

    file = request.files["file"]
    if file.filename == "" or not allowed_file(file.filename):
        return jsonify({"error": "Invalid or missing file"}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    try:
        # Extraction directe (synchronous)
        result_pydantic = extract_cv_data(file_path=filepath)
        result_dict = result_pydantic.model_dump()
        return jsonify(result_dict)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/status/<string:job_id>", methods=["GET"])
def get_job_status(job_id):
    job = JOBS.get(job_id)
    if not job:
        return jsonify({"error": "Job ID not found"}), 404
    return jsonify(job)


# ======================================================================
# --- MAIN ---
# ======================================================================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
