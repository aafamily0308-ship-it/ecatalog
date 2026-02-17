import argparse
import csv
import json
from urllib import request

from source_extractors import extract_offers_from_jsonld


def post_json(url: str, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with request.urlopen(req) as response:
        return json.loads(response.read().decode("utf-8"))


def import_rows(rows: list[dict], base_url: str) -> int:
    imported = 0
    for row in rows:
        product = post_json(
            f"{base_url}/api/products",
            {
                "title": row["title"],
                "brand": row.get("brand") or None,
                "category": row.get("category") or None,
                "condition": row["condition"],
            },
        )

        post_json(
            f"{base_url}/api/offers",
            {
                "product_id": product["id"],
                "seller": {
                    "name": row["seller_name"],
                    "city": row.get("seller_city") or None,
                },
                "price_azn": float(row["price_azn"]),
                "currency": row.get("currency") or "AZN",
                "url": row.get("url") or None,
                "is_available": True,
            },
        )
        imported += 1
    return imported


def load_csv_rows(file_path: str) -> list[dict]:
    with open(file_path, newline="", encoding="utf-8") as feed:
        reader = csv.DictReader(feed)
        return list(reader)


def load_jsonld_rows(source_url: str) -> list[dict]:
    with request.urlopen(source_url) as response:
        html = response.read().decode("utf-8", errors="ignore")
    return extract_offers_from_jsonld(html)


def main() -> None:
    parser = argparse.ArgumentParser(description="Import seller feed into eCatalog API")
    parser.add_argument("--file", help="Path to CSV feed")
    parser.add_argument("--source-url", help="Website page URL to parse JSON-LD offers when API is unavailable")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="API base URL")
    args = parser.parse_args()

    if not args.file and not args.source_url:
        raise SystemExit("Provide either --file or --source-url")

    rows: list[dict] = []
    if args.file:
        rows.extend(load_csv_rows(args.file))
    if args.source_url:
        rows.extend(load_jsonld_rows(args.source_url))

    imported = import_rows(rows, args.base_url)
    print(f"Feed import completed: {imported} offers")


if __name__ == "__main__":
    main()
