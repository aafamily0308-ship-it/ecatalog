# eCatalog MVP

Initial project scaffold for an Azerbaijan-focused product aggregator + marketplace (new and used items).

## What is included

- **Python backend API** with SQLite persistence.
- **Catalog + comparison endpoints** with approved-offer price comparison.
- **Moderation status flow** (`pending/approved/rejected`) for offers.
- **Price history tracking** for offers with timeline endpoint.
- **Seller cabinet API** (`/api/sellers/{name}/dashboard`) with offer stats and price-change counters.
- **Product card API** (`/api/products/{id}/card`) with aggregated offer data.
- **Extended filtering** by price/city/category/condition for products and offers.
- **Simple web UI** to browse products, apply filters, moderate status, update prices, load product cards and seller dashboards.
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

## API overview

- `POST /api/products`
- `GET /api/products?search=&category=&condition=&city=&min_price=&max_price=&status=`
- `GET /api/products/{id}/card`
- `POST /api/offers`
- `GET /api/offers?product_id=&status=&seller_name=&city=&min_price=&max_price=`
- `PATCH /api/offers/{id}/status`
- `PATCH /api/offers/{id}/price`
- `GET /api/offers/{id}/price-history`
- `GET /api/sellers/{name}/dashboard`
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

## Notes for websites without API

Many e-commerce pages expose `application/ld+json` Product/Offer metadata for SEO.
The importer supports extracting offers from this JSON-LD when direct API feeds are unavailable.
