import os
import json
import logging
import google.generativeai as genai
from flask import current_app

logger = logging.getLogger(__name__)

class AiService:
    def __init__(self):
        self.api_key = current_app.config.get("GEMINI_API_KEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-2.5-flash-lite')
        else:
            logger.warning("GEMINI_API_KEY not found. AI features will use mock data.")
            self.model = None

    def _mock_food_analysis(self, text: str) -> dict:
        """Fallback mock data for food analysis."""
        return {
            "food_name": text[:20],
            "kcal": 300,
            "protein_g": 15,
            "fat_g": 10,
            "carb_g": 40,
            "is_mock": True
        }

    def _mock_workout_analysis(self, text: str) -> dict:
        """Fallback mock data for workout analysis."""
        return {
            "workout_name": text[:20],
            "minutes": 30,
            "kcal_burn": 150,
            "is_mock": True
        }

    def analyze_food(self, text: str) -> dict:
        if not self.model:
            return self._mock_food_analysis(text)

        prompt = f"""
        Analyze the following food description and estimate the nutritional content.
        Return ONLY a JSON object with the following keys:
        - food_name: A concise name of the food (in Korean)
        - kcal: Estimated calories (float)
        - protein_g: Estimated protein in grams (float)
        - fat_g: Estimated fat in grams (float)
        - carb_g: Estimated carbohydrates in grams (float)

        Description: "{text}"
        JSON:
        """
        try:
            response = self.model.generate_content(prompt)
            # Cleanup potential markdown ticks if Gemini adds them
            clean_text = response.text.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_text)
        except Exception as e:
            logger.error(f"AI Food Analysis Failed: {e}")
            return self._mock_food_analysis(text)

    def analyze_workout(self, text: str) -> dict:
        if not self.model:
            return self._mock_workout_analysis(text)

        prompt = f"""
        Analyze the following workout description and estimate the energy burned.
        Return ONLY a JSON object with the following keys:
        - workout_name: A concise name of the workout (in Korean)
        - minutes: Estimated duration in minutes (int)
        - kcal_burn: Estimated calories burned (float)

        Description: "{text}"
        JSON:
        """
        try:
            response = self.model.generate_content(prompt)
            clean_text = response.text.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_text)
        except Exception as e:
            logger.error(f"AI Workout Analysis Failed: {e}")
            return self._mock_workout_analysis(text)
    def generate_tip(self, context: str) -> str:
        if not self.model:
            return "AI 서비스를 사용할 수 없습니다. (API Key Missing)"

        prompt = f"""
        You are a friendly and professional health coach.
        Based on the user's daily summary provided below, give a ONE-SENTENCE encouraging tip or advice in Korean.
        Do not mention accurate numbers, just qualitative advice.
        If they are doing well, praise them. If they are behind, encourage them safely.
        Tone: Empathetic, energetic, professional.

        User Summary:
        {context}

        Tip (Korean):
        """
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"AI Tip Generation Failed: {e}")
            return "오늘도 건강한 하루 보내세요! (AI 연결 실패)"
# Singleton helper (though typically instantiated per request or app context)
def get_ai_service():
    return AiService()
