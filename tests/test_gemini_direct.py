import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load .env manually
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

print(f"Checking API Key: {str(api_key)[:5]}...")

if not api_key:
    print("ERROR: GENIMI_API_KEY is not set in environment.")
    exit(1)

genai.configure(api_key=api_key)

# 1. List Models
print("\n--- Listing Available Models ---")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"- {m.name}")
except Exception as e:
    print(f"ERROR Listing Models: {e}")

# 2. Test Generation
model_name = 'gemini-1.5-flash'
print(f"\n--- Testing Generation with {model_name} ---")
try:
    model = genai.GenerativeModel(model_name)
    response = model.generate_content("Hello, can you hear me? Answer in 1 word.")
    print(f"SUCCESS! Response: {response.text}")
except Exception as e:
    print(f"ERROR Generating Content: {e}")
