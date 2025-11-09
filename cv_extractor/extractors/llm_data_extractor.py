# cv_extractor/extractors/llm_data_extractor.py
import json
import google.generativeai as genai
from ..config import GEMINI_API_KEY
from ..models.cv_models import ExtractedCV


class LlmDataExtractor:
    def __init__(self):
        genai.configure(api_key=GEMINI_API_KEY)
        # You can choose between "gemini-1.5-flash" (faster) or "gemini-1.5-pro" (more accurate)
        self.model_name = "gemini-1.5-pro"

    def extract(self, cv_text: str, nlp_skills: list) -> dict:
        nlp_skill_names = [skill.name for skill in nlp_skills]
        output_schema = ExtractedCV.model_json_schema()

        # --- Updated prompt for Gemini ---
        prompt = f"""
        You are an expert HR recruitment assistant. Your task is to analyze the following resume text and a list of skills found by an NLP tool.
        Your goal is to extract structured information, clean up the skill list, and infer new skills from work experience and projects.

        **Resume Text:**
        ---
        {cv_text}
        ---

        **Skills found by NLP Tool:**
        {nlp_skill_names}

        **Instructions:**
        1. Analyze Work Experience and extract structured work history.
        2. Analyze Projects and infer technologies used.
        3. Clean NLP skill list (remove junk, typos, duplicates).
        4. Merge all skills (NLP + inferred).
        5. Return valid JSON following this schema exactly:
        {json.dumps(output_schema, indent=2)}

        Return only valid JSON. No extra text, comments, or explanations.
        """

        model = genai.GenerativeModel(self.model_name)
        response = model.generate_content(prompt)

        try:
            # Gemini response text
            text = response.text.strip()
            # Extract JSON object (Gemini sometimes wraps in markdown ```json)
            if text.startswith("```"):
                text = text.strip("```").replace("json", "", 1).strip()
            return json.loads(text)
        except Exception as e:
            print("[GeminiExtractor] Error parsing response:", e)
            return {}
