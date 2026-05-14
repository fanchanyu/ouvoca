# LLM-ERP — Common Commands

## Backend

| Action                  | Command                                                        |
|-------------------------|----------------------------------------------------------------|
| Install                 | `pip install -r backend/requirements.txt`                       |
| Dev server (reload)     | `cd backend && uvicorn app.main:app --reload --port 8000`       |
| Seed DB                 | `cd backend && python -m scripts.seed`                          |
| Run all tests           | `cd backend && pytest`  *(once tests are added)*                |
| Lint                    | `cd backend && ruff check app/`                                 |
| Type check              | `cd backend && mypy app/`                                       |

## Factory MESH node

```bash
cd backend
FACTORY_ID=factory-a PORT=8001 python factory_node.py
```

## Database / Alembic

| Action              | Command                                                  |
|---------------------|----------------------------------------------------------|
| Create migration    | `cd backend && alembic revision --autogenerate -m "msg"` |
| Apply migrations    | `cd backend && alembic upgrade head`                     |
| Downgrade 1 rev     | `cd backend && alembic downgrade -1`                     |

## Frontend (desktop)

| Action      | Command                                  |
|-------------|------------------------------------------|
| Install     | `cd frontend-desktop && npm install`     |
| Dev         | `cd frontend-desktop && npm run dev`     |
| Build       | `cd frontend-desktop && npm run build`   |
| Type check  | `cd frontend-desktop && npx tsc --noEmit`|

## Docker

| Action          | Command                                                 |
|-----------------|---------------------------------------------------------|
| Start stack     | `docker compose up -d --build`                          |
| Seed in stack   | `docker compose exec backend python -m scripts.seed`    |
| Tail logs       | `docker compose logs -f backend`                        |
| Stop            | `docker compose down`                                   |
| Reset (wipe vol)| `docker compose down -v`                                |

## URLs (default)

- Desktop UI: <http://localhost:5173>  · login `admin` / `admin123` or Demo Mode
- API docs:   <http://localhost:8000/docs>
- War-room:   <http://localhost:8080>
- Factory A:  <http://localhost:8001/api/factory/health>
- Factory B:  <http://localhost:8002/api/factory/health>
