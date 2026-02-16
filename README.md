# eCatalog MVP

Initial project scaffold for an Azerbaijan-focused product aggregator + marketplace (new and used items).

## What is included

- **Python backend API** with SQLite persistence.
- **Product + offer endpoints** for catalog and price comparison.
- **Simple web UI** to browse products and compare offers.
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

## Import feed example

```bash
python scripts/import_feed.py --file sample_feed.csv
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
