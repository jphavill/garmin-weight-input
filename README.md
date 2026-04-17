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
- Uses one production update path: `PUT /activity-service/activity/{id}` on `connectapi` with a minimal payload.
- Updates activity type to `rucking` and sets `summaryDTO.beginPackWeight` to the converted grams value.
- Renames activity title by replacing `Hiking` with `Rucking` via explicit activity-name update.

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
  "update_method": "connectapi_put_minimal",
  "pack_weight": 5.0
}
```

### Shoe wear distance summary

`/shoe-wear` returns running, walking, and rucking distance totals (km) plus per-activity details for a date range.

```bash
curl "http://localhost:8002/shoe-wear?start_date=2026-01-01&end_date=2026-01-31"
```

`/shoe-wear` behavior:

- Requires `start_date` and `end_date` query params in `YYYY-MM-DD` format.
- Returns `400` if `start_date` is after `end_date`.
- Fetches Garmin activities for `running`, `walking`, and `hiking`.
- Applies local ruck classification to hiking activities and includes only classified rucks in the `rucking` bucket.
- Returns totals rounded to 2 decimals, activity counts, and normalized activity arrays.

Example success response:

```json
{
  "startDate": "2026-01-01",
  "endDate": "2026-01-31",
  "totals": {
    "totalKm": 42.35,
    "runningKm": 18.9,
    "walkingKm": 12.45,
    "ruckingKm": 11.0
  },
  "activityCounts": {
    "running": 5,
    "walking": 4,
    "rucking": 3
  },
  "activities": {
    "running": [
      {
        "activityId": 123,
        "activityName": "Morning Run",
        "startTimeLocal": "2026-01-03 07:12:01",
        "distanceKm": 5.25
      }
    ],
    "walking": [],
    "rucking": []
  }
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
