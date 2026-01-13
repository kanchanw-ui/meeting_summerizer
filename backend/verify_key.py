import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
print(f"Checking Key: {api_key[:5]}...{api_key[-5:]}")

if not api_key:
    print("No API Key found!")
    exit(1)

genai.configure(api_key=api_key)

try:
    print("Listing available models...")
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(m.name)
            
    models_to_test = [
        'gemini-1.5-flash',
        'gemini-2.0-flash-lite-preview-02-05',
        'gemini-flash-latest',
        'gemini-pro'
    ]
    
    for model_name in models_to_test:
        try:
            print(f"\nTesting {model_name}...")
            model = genai.GenerativeModel(model_name)
            response = model.generate_content("Say 'Working'")
            print(f"SUCCESS with {model_name}: {response.text}")
        except Exception as e:
            print(f"FAILED {model_name}: {e}")

except Exception as e:
    print("\nOUTER FAILURE:")
    print(e)
