import os
import json
import requests
from dotenv import load_dotenv
from pathlib import Path

# Load env variables
load_dotenv()

APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbxCy6pAA6QKGtKJODbq-IF1qglK2nX9wtUpvnGm3jzGXHu_fMS_Mn10uLUeQX3qtVQB/exec"
# List of sheet names (based on your tabs)
SHEETS = [
    "Tracker",
]

# Ensure db folder exists
db_path = Path("db")
db_path.mkdir(exist_ok=True)

def fetch_sheet(sheet_name: str):
    """Fetch one sheet's data from Apps Script endpoint."""
    url = f"{APPS_SCRIPT_URL}"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

def save_json(sheet_name: str, data: dict):
    """Save JSON data to db/<sheet_name>.json"""
    file_path = db_path / f"{sheet_name.replace(' ', '_')}.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✅ Saved {sheet_name} → {file_path}")

def main():
    for sheet in SHEETS:
        try:
            data = fetch_sheet(sheet)
            save_json(sheet, data)
        except Exception as e:
            print(f"❌ Failed to fetch {sheet}: {e}")

if __name__ == "__main__":
    main()

