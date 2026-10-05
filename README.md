# House Price Prediction

An educational end-to-end machine learning project that uses French DVF sales
data to estimate the price of a single home. It currently includes a first
Ridge baseline trained on the 2025 cohort, a FastAPI inference endpoint and a
small React form that calls it.

## Architecture

```text
User → React frontend → FastAPI backend → ML prediction service → scikit-learn model
```

The API exposes root and health routes plus `POST /api/v1/predictions`. The
React form sends its request through Vite's `/api` development proxy, so local
browser requests reach FastAPI without requiring separate CORS configuration.
The form loads departments and commune/postal-code choices from the official
French [Géo API](https://geo.api.gouv.fr/), through
`GET /api/v1/locations/departments` and
`GET /api/v1/locations/departments/{code}/communes`. These lists are cached
in the API process. The prediction endpoint independently checks that the
submitted department, DVF commune code, and postal code match the reference.
The full INSEE commune identifier is converted to the suffix used by DVF; codes
remain strings so leading zeroes are preserved.
The browser therefore requires access to the backend and the backend requires
internet access to refresh the official geographic lists.
Prediction responses include an explanation based on each input's contribution
to the fitted Ridge model in log-price space. The model has no transport or
metro-station feature, so these are not inferred or described as causes.
Contributions are statistical associations relative to the model's encoded
baseline, not causal effects or guarantees.
The prediction route validates property details and loads the locally trained
2025 Ridge artifact on its first request. It returns `503` when that artifact
is missing. The artifact itself is ignored by Git.

## Tech stack

- Python 3.12+, FastAPI, Uvicorn, Pydantic
- Pandas, NumPy, scikit-learn, Matplotlib, Seaborn, Jupyter
- React, TypeScript, Vite
- Pytest, Ruff, GitHub Actions, Docker Compose

## Project structure

```text
backend/       FastAPI application and backend tests
frontend/      React/Vite interface, organized for future components and services
data/          raw and processed dataset locations
notebooks/     exploratory notebooks
ml/            preprocessing, training, evaluation, and model artifacts
tests/         space for future cross-project tests
.github/       CI workflows
docs/          project documentation
```

## Local setup

Prerequisites: Python 3.12+, Node.js 22+ and npm. Docker Compose is optional.

```bash
git clone <repository-url>
cd hause
python -m venv .venv
source .venv/bin/activate       # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
```

`requirements.txt` contains API and model-inference runtime dependencies. The
development file adds the data/ML stack plus test and lint tools; the backend
container installs only the runtime set. To enable predictions locally, first
generate `ml/models/ridge_2025_full.joblib` with the training command below.

Run the backend from the repository root:

```bash
uvicorn backend.app.main:app --reload
```

The API is at `http://localhost:8000`; interactive docs are at `/docs`.

Example request to the prediction endpoint:

```bash
curl -X POST http://localhost:8000/api/v1/predictions \
  -H 'Content-Type: application/json' \
  -d '{"property_type":"Appartement","built_area_m2":75,"rooms":3,"department_code":"75","commune_code":"056","postal_code":"75006"}'
```

Run the frontend in a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Vite serves the page at `http://localhost:5173`.
The form starts with sample values; submit them to exercise the full browser →
API → model path. Department, commune, and postal code must be selected from
the dependent lists. For local development the Vite proxy expects the API at
`http://localhost:8000`; Docker Compose routes it to the `backend` service.

Run quality checks from the repository root:

```bash
pytest
ruff check .
```

Run the frontend interaction tests and production build from `frontend/`:

```bash
npm test
npm run build
```

Create the first filtered DVF working table (the original raw file is not
modified):

```bash
python ml/preprocessing/prepare_dvf.py
```

The script keeps exact `Vente` house/apartment rows with price, built area and
room count present, removes only source rows identical across all original
columns, and writes a compact table under `data/processed/`. Generated data is
ignored by Git.

Run the development containers from the repository root:

```bash
docker compose up --build
```

This exposes the backend on port 8000 and frontend on 5173. The backend image
includes `ml/models/ridge_2025_full.joblib` when that local artifact exists. The
model stays out of Git and other generated model files are excluded from the
Docker build context. Without the artifact, the containers still build and the
API's prediction endpoint responds with `503` until a model is provided. If
these ports are already occupied, set `API_HOST_PORT` and
`FRONTEND_HOST_PORT` in `.env` to available host ports.

## Configuration and data

`.env.example` documents future local settings. Copy it to `.env` when needed;
`.env` is ignored by Git. Keep secrets and large or licensed datasets out of the
repository. See `data/README.md` before adding a dataset.

## Git workflow

The intended workflow uses `main` for stable code, `develop` for integration,
and short-lived `feature/<name>` branches for focused work. Open pull requests
from feature branches into `develop`; promote reviewed, working milestones from
`develop` to `main`. Only the existing default branch is initialized at this
stage; no extra branches are created automatically.

## CI/CD roadmap

The GitHub Actions workflow runs Ruff and Pytest for the backend, frontend
interaction tests and a production build, then builds both Docker Compose
images on pushes and pull requests targeting `main`. Render watches `main`
and deploys the web service after each pushed commit.

```text
Code → Git → GitHub → CI (tests, lint, build) → Docker → CD → Cloud deployment
```

## Déploiement sur Render

Le fichier `render.yaml` décrit un service web Docker unique. L’image compile
le frontend React puis le sert avec FastAPI ; les appels `/api` restent ainsi
sur la même origine. Le service vérifie sa disponibilité sur `/health`.
L’artefact `ml/models/ridge_2025_full.joblib` est inclus dans le dépôt pour
que les prédictions soient disponibles au déploiement. Les fichiers DVF bruts
et préparés demeurent ignorés par Git.

Pour créer le service, connecter le dépôt GitHub à Render, choisir
**New > Blueprint**, puis sélectionner ce dépôt et le fichier `render.yaml`.
Render construira et publiera automatiquement l’application sur son URL
`onrender.com`. Le niveau gratuit peut mettre le service en veille après une
période d’inactivité ; la première requête suivante peut donc prendre plus de
temps.

## Modèle et limites

Le service utilise les caractéristiques de la cohorte 2025 (`built_area_m2`,
`rooms`, type de bien et codes géographiques). La date n'est pas une variable
du modèle. Le millésime est renvoyé dans la réponse pour rappeler qu'une
estimation réalisée plus tard reste fondée sur le marché observé en 2025, et
ne constitue pas une prévision de son évolution. Le modèle n'expose pas encore
d'intervalle de confiance.

## Analyse des données

Après la préparation, l’analyse exploratoire et les contrôles de distributions sont dans [`notebooks/02_data_analysis.ipynb`](notebooks/02_data_analysis.ipynb). Les observations extrêmes et doublons sur les colonnes exportées y sont documentés, sans suppression automatique.

## Cohorte candidate pour le modèle

L’objectif de modélisation est le prix d’un seul logement vendu. Le script `python ml/preprocessing/prepare_single_home_candidates.py` produit une cohorte candidate à partir du fichier source en comptant les lignes résidentielles dans des groupes consécutifs date + prix, puis écarte les groupes avec d’autres locaux bâtis que les dépendances. Cette clé reste une heuristique, pas une preuve d’identité de mutation. Les limites et les comparaisons sont décrites dans [`data/README.md`](data/README.md) et [`notebooks/03_single_home_cohort.ipynb`](notebooks/03_single_home_cohort.ipynb).

## Premier modèle

Après avoir créé la cohorte candidate, lancer `python ml/training/train_baseline.py` pour comparer des références médianes, un Ridge et un Histogram Gradient Boosting sur log-prix avec une validation temporelle. Les métriques globales, par type et par tranche de prix sont enregistrées dans `ml/evaluation/baseline_metrics.json`. Après la comparaison, ajouter `--refit-ridge-on-full-year` pour entraîner l’artefact final sur tout 2025 ; les modèles dans `ml/models/` sont ignorés par Git. Le protocole est expliqué dans [`notebooks/04_baseline_evaluation.ipynb`](notebooks/04_baseline_evaluation.ipynb), et l’analyse des erreurs et des prix élevés dans [`notebooks/05_error_analysis.ipynb`](notebooks/05_error_analysis.ipynb).

Pour garder des comparaisons reproductibles, les versions de modèle de ce projet utilisent le millésime 2025. Une prédiction future avec ce modèle reste une estimation fondée sur le marché observé en 2025, et non une prévision de l’évolution du marché.
