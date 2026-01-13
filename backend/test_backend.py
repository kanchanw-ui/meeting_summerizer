import requests
import json

url = "http://localhost:8000/generate"
data = {
    "transcript": "This is a test meeting transcript. We discussed the project timeline. John agreed to finish the report by Friday. Sarah will handle the client communication."
}

try:
    print("Sending request to backend...")
    response = requests.post(url, json=data)
    print(f"Status Code: {response.status_code}")
    print("Response:")
    print(json.dumps(response.json(), indent=2))
except Exception as e:
    print(f"Error: {e}")
