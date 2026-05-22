# dtm-quiz-bot

Telegram bot for Uzbekistan university entrance exam preparation. Stage 1 is a clean MVP foundation: students can start a short DTM-style quiz, see explanations after each answer, save the attempt, and view basic statistics.

## Features

- `/start` welcome flow with a simple main menu
- 5-question sample quiz loaded from JSON
- Preparation source references before each test
- Inline answer buttons
- Immediate correct/incorrect feedback with explanations
- Saved attempts and answer results in PostgreSQL
- Basic statistics: total attempts, average accuracy, best result, latest result
- Docker and Docker Compose setup
- Alembic migration for the initial database schema

## Tech Stack

- Python 3.12
- aiogram 3.x
- PostgreSQL
- SQLAlchemy 2.x async
- asyncpg
- Alembic
- Docker and Docker Compose
- pydantic-settings with `.env`
- pytest

## Project Structure

```text
bot/
  main.py
  config.py
  loader.py
  keyboards.py
  handlers/
    start.py
    quiz.py
    stats.py
    admin.py
  services/
    quiz_service.py
    stats_service.py
  db/
    database.py
    models.py
data/
  questions.example.json
alembic/
  versions/
tests/
docs/
scripts/
.env.example
README.md
requirements.txt
Dockerfile
docker-compose.yml
```

## Environment Variables

Create a local `.env` file from the safe example:

```bash
cp .env.example .env
```

Then edit `.env`:

```env
BOT_TOKEN=your-real-telegram-bot-token
DATABASE_URL=postgresql+asyncpg://dtm_user:dtm_password@postgres:5432/dtm_quiz_bot
ADMIN_IDS=123456789,987654321
QUESTIONS_FILE=data/questions.example.json
```

`ADMIN_IDS` can be empty for Stage 1.

## Docker Setup

Start the bot and PostgreSQL:

```bash
docker compose up -d --build
```

The bot service runs migrations automatically before starting.

Useful commands:

```bash
docker compose logs -f bot
docker compose down
docker compose down -v
```

Use `docker compose down -v` only when you want to remove the PostgreSQL volume and lose local data.

## Local Setup

For local development without Docker:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

If you run the bot outside Docker, set `DATABASE_URL` to a database host reachable from your machine, for example:

```env
DATABASE_URL=postgresql+asyncpg://dtm_user:dtm_password@localhost:5432/dtm_quiz_bot
```

Run migrations:

```bash
alembic upgrade head
```

Start the bot:

```bash
python -m bot.main
```

Run tests:

```bash
pytest
```

## Database Migrations

Apply migrations:

```bash
alembic upgrade head
```

Create a new migration after changing models:

```bash
alembic revision --autogenerate -m "describe change"
```

Review generated migrations before committing them.

## Updating Questions

The sample quiz reads from `QUESTIONS_FILE`.

For public demo data, edit:

```text
data/questions.example.json
```

For private/local data, create:

```text
data/questions.json
```

Then set:

```env
QUESTIONS_FILE=data/questions.json
```

Each question must include:

- `id`
- `subject`
- `topic`
- `subtopic`
- `question`
- `options`
- `correct_index`
- `explanation_correct`
- `wrong_explanations`
- `difficulty`
- `source_refs`

## Security Notes

- Do not commit `.env`.
- Do not commit a real Telegram bot token.
- Do not commit copyrighted PDFs.
- Do not commit full private question banks.
- Keep `data/questions.json` private; use `data/questions.example.json` for safe sample data.
