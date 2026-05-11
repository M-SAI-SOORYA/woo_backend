# Woo Habit Backend

Python API for the gamified habit tracker.

## Run locally

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 5000
```

The API stores data in MongoDB. Create `woo_backend/.env` from `.env.example`
and set your MongoDB Atlas connection string:

```bash
MONGO_URI=mongodb+srv://<username>:<password>@<cluster-url>/woo_habits?retryWrites=true&w=majority
MONGO_DB_NAME=woo_habits
```

For Atlas, make sure your database user has read/write access and your current
IP address is allowed in Network Access.

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
