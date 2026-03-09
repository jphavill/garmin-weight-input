#!/usr/bin/env python3
"""Initial authentication script to generate Garmin session token."""
import os
import sys
from pathlib import Path
import garth
from garth.exc import GarthException

DATA_DIR = Path(__file__).parent / "data"
GARTH_FILE = DATA_DIR / "garth_token"

def main():
    email = os.getenv("GARMIN_EMAIL")
    password = os.getenv("GARMIN_PASSWORD")
    
    if not email or not password:
        print("Error: GARMIN_EMAIL and GARMIN_PASSWORD must be set in .env")
        sys.exit(1)
    
    print(f"Authenticating with Garmin as {email}...")
    
    DATA_DIR.mkdir(exist_ok=True)
    
    garth.login(email, password)
    garth.save(GARTH_FILE)
    print(f"Garth session saved to {GARTH_FILE}")
    print("You can now start the container.")


if __name__ == "__main__":
    main()
