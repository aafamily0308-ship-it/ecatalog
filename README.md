# eCatalog MVP

Initial project scaffold for an Azerbaijan-focused product aggregator + marketplace (new and used items).

## Current state

- ✅ **Phase 1 complete**: catalog/filtering, moderation, price history, product cards, seller dashboard.
- 🚧 **Phase 2 started**: reviews/ratings, seller verification, price alerts, fraud signals.

## What is included

- **Python backend API** with SQLite persistence.
- **Catalog + comparison endpoints** with approved-offer price comparison.
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
- **Fraud signal APIs**:
  - `POST /api/fraud-signals`
  - `GET /api/fraud-signals`
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
python -m unittest discover -s tests
```
