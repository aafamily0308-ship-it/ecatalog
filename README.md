# eCatalog MVP

Initial project scaffold for an Azerbaijan-focused product aggregator + marketplace (new and used items).

## What is included

- **Python backend API** with SQLite persistence.
- **Product + offer endpoints** for catalog and price comparison.
- **Moderation status flow** (`pending/approved/rejected`) for offers.
- **Price history tracking** for offers with timeline endpoint.
- **Simple web UI** to browse products, create offers, moderate status, and update prices.
- **CSV ingestion script** to import offers from partner feeds.
- **Automated tests** using standard library + pytest (if available).

## Quick start

```bash
python -m apps.api.main
```

Then open http://127.0.0.1:8000.

## Run tests

```bash
python -m unittest discover -s tests
```

## API overview

- `POST /api/products`
- `GET /api/products`
- `POST /api/offers`
- `GET /api/offers`
- `PATCH /api/offers/{id}/status`
- `PATCH /api/offers/{id}/price`
- `GET /api/offers/{id}/price-history`
- `GET /api/compare/{product_id}` (uses only approved offers)

## Import feed examples

CSV import:

```bash
python scripts/import_feed.py --file sample_feed.csv
```

If a marketplace has no API, parse public product page JSON-LD:

```bash
python scripts/import_feed.py --source-url https://example.com/product-page
```

CSV columns:

- `title`
- `brand`
- `category`
- `condition` (`new`, `used`, `refurbished`)
- `seller_name`
- `seller_city`
- `price_azn`
- `currency`
- `url`

## Notes for websites without API

Many e-commerce pages expose `application/ld+json` Product/Offer metadata for SEO.
The importer supports extracting offers from this JSON-LD when direct API feeds are unavailable.
