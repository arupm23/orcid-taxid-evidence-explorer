# Run the MVP from your Desktop

These instructions are for macOS and use the public GitHub repository.

## 1. Open Terminal and download the project

```bash
cd ~/Desktop
git clone https://github.com/arupm23/orcid-taxid-evidence-explorer.git
cd orcid-taxid-evidence-explorer
```

If the project already exists on your Desktop, update it instead:

```bash
cd ~/Desktop/orcid-taxid-evidence-explorer
git pull
```

## 2. Create and activate the Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## 3. Create the local configuration

```bash
cp .env.example .env
open -e .env
```

In the file that opens, replace `you@example.org` with your email address. NCBI requests API clients to identify themselves. You can leave `NCBI_API_KEY` empty for an initial demonstration.

Save and close the file, then load the settings:

```bash
set -a
source .env
set +a
```

## 4. Start the application

```bash
python run.py
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.

Keep the Terminal window open while using the application. Press `Control+C` in Terminal to stop it.

## Run it again later

```bash
cd ~/Desktop/orcid-taxid-evidence-explorer
source .venv/bin/activate
set -a
source .env
set +a
python run.py
```

## Run the automated tests

```bash
cd ~/Desktop/orcid-taxid-evidence-explorer
source .venv/bin/activate
python -m unittest discover -s tests -v
```
