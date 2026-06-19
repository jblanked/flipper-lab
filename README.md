# Flipper Lab
Open source Flipper Zero app hub.

## Requirements
- Python >= 3.9 and < 3.14

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

4. Install the required dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### First-time setup
1. Migrate the database:
```bash
python manage.py migrate
```

2. Create a superuser to access the admin panel:
```bash
python manage.py createsuperuser
```

3. Run the development server:
```bash
python manage.py runserver
```

4. Access the application in your web browser at `http://127.0.0.1:8000/`

5. Sync the database with the Flipper Zero app catalog by visiting `http://127.0.0.1:8000/api/sync/`. It starts a background task to fetch the latest app data from the Flipper Zero app catalog and update the local database accordingly. You can check the status of the sync task in the admin panel under `Sync Runs`. It may take up to 30 minutes due to Github API rate limits (it sleeps 3 seconds between each app). You can stop an ongoing sync by visiting `http://127.0.0.1:8000/api/sync/stop/`.

### Regular usage
1. Start the development server:
```bash
python manage.py runserver
```

2. Access the application in your web browser at `http://127.0.0.1:8000/`