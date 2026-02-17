# eCatalog MVP

Initial project scaffold for an Azerbaijan-focused product aggregator + marketplace (new and used items).

## Current state

- ✅ **Phase 1 complete**: catalog/filtering, moderation, price history, product cards, seller dashboard.
- ✅ **Phase 2 (MVP scope) complete**: reviews/ratings, seller verification, price alerts, fraud registry + auto-scan + alert processing.
- ✅ **Phase 3 backend complete**: full data-management APIs (CRUD for products, offer deletion, staged update/delete, alert deactivation) for operator-grade admin workflows.

## What is included

- **Python backend API** with SQLite persistence.
- **Catalog + comparison endpoints** with approved-offer price comparison.
- **Full product lifecycle APIs**:
  - `GET /api/products/{id}`
  - `PUT /api/products/{id}`
  - `DELETE /api/products/{id}` (cascade delete offers/history/alerts)
- **Offer lifecycle APIs**:
  - `DELETE /api/offers/{id}`
- **Staging lifecycle APIs**:
  - `PATCH /api/admin/staged/products/{id}`
  - `DELETE /api/admin/staged/products/{id}`
  - `PATCH /api/admin/staged/offers/{id}`
  - `DELETE /api/admin/staged/offers/{id}`
- **Moderation status flow** (`pending/approved/rejected`) for offers.
- **Price history tracking** for offers with timeline endpoint.
- **Seller cabinet API** (`/api/sellers/{name}/dashboard`) with offer stats and price-change counters.
- **Seller trust APIs**:
  - `PATCH /api/sellers/{name}/verify`
  - `POST /api/sellers/{name}/reviews`
  - `GET /api/sellers/{name}/reviews`
- **Retention APIs**:
  - `POST /api/alerts`
  - `GET /api/alerts`
  - `POST /api/alerts/{id}/deactivate`
  - `POST /api/alerts/process`
- **Fraud signal APIs**:
  - `POST /api/fraud-signals`
  - `GET /api/fraud-signals`
  - `POST /api/fraud-signals/auto-scan`
- **Simple web UI** for product/offer management, moderation, trust workflows and analytics views.
- **CSV + JSON-LD ingestion script** for marketplaces with and without APIs.
- **Automated tests**.

## Quick start

```bash
python -m apps.api.main
```

Then open http://127.0.0.1:8000.

## Run tests

```bash
python -m pytest -q
```


## Service operations (start/stop/logs)

```bash
scripts/run_site.sh start
scripts/run_site.sh status
scripts/run_site.sh logs
scripts/run_site.sh stop
```

This writes runtime logs to `ecatalog.log` (or `$ECATALOG_LOG_FILE`).

## Automated diagnostics collection (remote-friendly)

```bash
python scripts/collect_diagnostics.py --base-url http://127.0.0.1:8000 --log-file ecatalog.log --output diagnostics_report.json
```

The report includes:
- `/health` response,
- `/api/diagnostics/summary` snapshot,
- tail of runtime logs.


## Phase readiness check (Phase 1 + 2)

```bash
python scripts/check_phases.py --base-url http://127.0.0.1:8000
```

Outputs a JSON report with `phase1_ok` and `phase2_ok` flags.


## Visual overview (what you can see in browser now)

Open `http://127.0.0.1:8000` and you can visually use:
- Product creation form,
- Offer creation form,
- Moderation form (pending/approved/rejected),
- Price update + price history viewer,
- Phase 2 trust tools (seller verification, review submission, alert creation, fraud signal submission),
- Catalog filters panel,
- Product card JSON panel,
- Seller dashboard JSON panel,
- Seller reviews JSON panel,
- Alerts and fraud signals JSON panels.

Latest UI screenshot artifact: `phase2-complete-ui.png`
