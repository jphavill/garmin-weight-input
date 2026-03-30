# Garmin Weight Input API

FastAPI service to log weight to Garmin Connect and convert recent hikes to rucking.

## Setup

1. Copy `.env.example` to `.env` and add your Garmin credentials:
   ```bash
   cp .env.example .env
   # Edit .env with your GARMIN_EMAIL and GARMIN_PASSWORD
   ```

2. Initial authentication (run this locally before starting the container):
   ```bash
   pip install -r requirements.txt
   python init_auth.py
   ```

3. Build and start the container:
   ```bash
   docker-compose up -d
   ```

4. Set your timezone in `docker-compose.yml` (default is UTC). Find your timezone at https://en.wikipedia.org/wiki/List_of_tz_database_time_zones and update the `TZ` environment variable.

## Running tests

```bash
source /Users/jphavill/Documents/github/garmin-weight-input/.venv/bin/activate
pytest -q
```

## Usage

### Log weight
```bash
curl -X POST http://localhost:8002/weight \
  -H "Content-Type: application/json" \
  -d '{"weight": 78.1}'
```

### Convert latest hike to rucking
```bash
curl -X POST http://localhost:8002/hike-to-ruck \
  -H "Content-Type: application/json" \
  -d '{"pack_weight": 5.0}'
```

`/hike-to-ruck` behavior:

- Finds the latest Garmin activity.
- Requires the activity to be a hiking activity and started within the last 8 hours.
- Accepts `pack_weight` in kilograms and converts to grams before sending to Garmin.
- Converts activity type from hiking to rucking.
- Sets `summaryDTO.beginPackWeight` to the converted grams value.
- Renames activity title by replacing `Hiking` with `Rucking`.

Example success response:

```json
{
  "message": "Latest hiking activity converted to rucking",
  "activity_id": 22342784267,
  "old_type": "hiking",
  "new_type": "rucking",
  "pack_weight_grams": 5000,
  "original_activity_name": "Halifax Hiking",
  "new_activity_name": "Halifax Rucking",
  "garmin_activity_name_after_update": "Halifax Rucking",
  "pack_weight": 5.0
}
```

### Health check
```bash
curl http://localhost:8002/health
```

## iOS Shortcuts Setup

1. Create a new Shortcut
2. Add "URL" action pointing to your server (e.g., `http://your-server:8002/weight`)
3. Add "Get Contents of URL" action:
   - Method: POST
   - Headers: `Content-Type: application/json`
   - Request Body: JSON Dictionary with `weight`
4. Use "Ask for Input" action to get weight from user
