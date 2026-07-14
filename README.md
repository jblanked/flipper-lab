# Flipper Lab
Open source Flipper Zero app hub.

## Architecture

The project is split into two parts plus a vendored build tool:

- **`backend/`** — a Django + Django REST Framework API.
- **`frontend/`** — a SvelteKit app. Browses the catalog and talks to a connected
  Flipper Zero over WebSerial.
- **`flipperzero-ufbt-app/`** — a git submodule providing the `ufbt`-based build
  pipeline the backend calls to compile apps. Treated as read-only.
- **`build_workspace/`** — scratch directory for downloaded repos and build
  artifacts (created automatically; kept outside the backend so it doesn't
  trigger Django's autoreloader).


## Requirements
- **Python** >= 3.9 and < 3.14
- **Node.js** >= 20 (for the frontend)
- **git** — required at runtime for building apps and for update detection
  (the backend uses `git ls-remote` to resolve app source commits)
- **A browser with webserial support**

## Installation
1. Clone the repository:
```bash
git clone https://github.com/your-username/flipper-lab.git
cd flipper-lab
```

2. Fetch the submodule:
```bash
git submodule update --init --recursive
```

### Backend
3. Create a virtual environment and activate it:

**Windows  (Using Windows PowerShell):**
```bash
python -m venv venv
./venv/Scripts/activate
```

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

(If you have a newer version of python installed there are various ways to have a downgraded venv but I recommend uv since it sets it up in a single command and you can still use pip normally)

4. Install the backend dependencies:
```bash
pip install -r requirements.txt
```

### Frontend

5. Install the frontend dependencies:
```bash
   cd frontend
   npm install
   cd ..
```

Protobuf definitions for Flipper RPC are generated automatically before
`dev`/`build` (via the `predev`/`build` npm scripts), so no extra step is
needed.

## Usage

## First-time setup

Run these from the `backend/` directory with the virtual environment active.
 
1. Create and apply the database migrations, then seed the firmware list:
```bash
   python manage.py makemigrations
   python manage.py migrate
   python manage.py seed_firmware
```

   The app runs on SQLite by default. `seed_firmware` populates the supported
   firmware rows (Official, Momentum, Unleashed, RogueMaster) and is idempotent.

2. (Optional) Create a superuser to access the Django admin:
```bash
   python manage.py createsuperuser
```

3. Populate the catalog by syncing with the Flipper Zero app catalog. Start the
   backend (see below), then trigger a sync:
```
   http://127.0.0.1:8000/api/sync/
```

   This kicks off a background task that fetches the latest app data. It can take
   a while (it sleeps a few seconds between apps to respect GitHub API rate
   limits). Stop an in-progress sync with:

```
   http://127.0.0.1:8000/api/sync/stop/
```

(Note: this needs fixing, I got rate limited consistently)

### Regular usage

Run the backend and frontend in two terminals.

**Backend** (from `backend/`, venv active):

```bash
python manage.py runserver
```

Serves the API at `http://127.0.0.1:8000/`.

**Frontend** (from `frontend/`):

```bash
npm run dev
```

Serves the app at the URL Vite prints (typically `http://localhost:5173/`). The
frontend proxies `/api` requests to the Django backend, so both need to be
running.
