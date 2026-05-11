# Woo Habit Backend

Python API for the gamified habit tracker.

## Run locally

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 5000
```

The API stores data in `woo_habits.db` in this backend directory by default,
even if the server is started from another working directory. Override it with:

```bash
set DATABASE_PATH=path\to\custom.db
```

## Main endpoints

- `GET /api/dashboard`
- `GET /api/habits`
- `POST /api/habits`
- `PATCH /api/habits/{habit_id}`
- `DELETE /api/habits/{habit_id}`
- `POST /api/checkins`
- `GET /api/history`

Legacy frontend endpoints are also supported:

- `GET /get/item1`
- `GET /get/items`
- `POST /xp`
- `POST /datexp`
