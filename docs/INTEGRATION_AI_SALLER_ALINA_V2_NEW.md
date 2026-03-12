# Integration with AI-Saller-Alina-v2-new

This guide connects `ai-sales-analytics` to the existing bot database from:

- `/Users/alinasemicheva/Documents/AI инженер/AI seller Alina v2/AI-Saller-Alina-v2-new`

## 1) Pick DB source

### Option A: local SQLite from the bot project

Use bot file:

- `/Users/alinasemicheva/Documents/AI инженер/AI seller Alina v2/AI-Saller-Alina-v2-new/local.db`

Set in analytics `.env`:

```env
DATABASE_URL=sqlite:////Users/alinasemicheva/Documents/AI инженер/AI seller Alina v2/AI-Saller-Alina-v2-new/local.db
SCHEMA_MAPPING_PATH=config/schema_mapping.alina_v2_new.yaml
DEFAULT_TIMEZONE=Europe/Moscow
```

### Option B: PostgreSQL from docker compose

If bot runs on PostgreSQL, set:

```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/ai_sales_manager
SCHEMA_MAPPING_PATH=config/schema_mapping.alina_v2_new.yaml
DEFAULT_TIMEZONE=Europe/Moscow
```

## 2) Install and run analytics

```bash
python3 -m pip install -e .[dev]
ai-sales-analytics run-daily --report-date 2026-03-12
```

Output artifacts:

- `reports/2026-03-12/analytics.json`
- `reports/2026-03-12/report.html`
- `reports/2026-03-12/charts/*.png`

## 3) Run as API

```bash
ai-sales-analytics serve
```

Then:

```bash
curl "http://localhost:8000/analytics/daily?report_date=2026-03-12"
```

## 4) Daily automation

```bash
ai-sales-analytics scheduler
```

Configure cron in `.env` via `DAILY_REPORT_CRON`.

## 5) Notes for this specific bot schema

`AI-Saller-Alina-v2-new` has:

- `leads`, `messages`, `ai_runs`, `services`
- no dedicated `bookings` table
- no dedicated `stage_events` table
- no dedicated `follow_ups` table

How analytics adapts:

- `leads.booking_slot_at` is used as target action timestamp
- stage flow is reconstructed from current stage + intent traces
- handoff is inferred from `ai_runs.raw_response` and message semantics

If you later add explicit tables (`bookings`, `stage_events`, `follow_ups`), extend mapping and analytics will pick them up automatically.
