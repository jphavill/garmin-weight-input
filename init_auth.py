#!/usr/bin/env python3
"""Initial authentication script to generate Garmin session tokens."""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from garminconnect import Garmin

DATA_DIR = Path(__file__).parent / "data"
TOKEN_STORE_DIR = DATA_DIR / "garmin_tokens"
TOKEN_STORE_FILE = TOKEN_STORE_DIR / "garmin_tokens.json"


def main():
    load_dotenv()

    email = os.getenv("GARMIN_EMAIL")
    password = os.getenv("GARMIN_PASSWORD")

    if not email or not password:
        print("Error: GARMIN_EMAIL and GARMIN_PASSWORD must be set in .env")
        sys.exit(1)

    print(f"Authenticating with Garmin as {email}...")

    TOKEN_STORE_DIR.mkdir(parents=True, exist_ok=True)

    try:
        client = Garmin(email, password, prompt_mfa=lambda: input("MFA code: ").strip())
        client.login(str(TOKEN_STORE_DIR))
    except Exception as exc:
        print(f"Authentication failed: {exc}")
        sys.exit(1)

    if not TOKEN_STORE_FILE.exists():
        print(f"Authentication succeeded but token file was not created at {TOKEN_STORE_FILE}")
        sys.exit(1)

    print(f"Garmin tokens saved to {TOKEN_STORE_FILE}")
    print("You can now start the container.")


if __name__ == "__main__":
    main()
