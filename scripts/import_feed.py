import argparse
import csv
import json
from urllib import request


def post_json(url: str, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with request.urlopen(req) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Import seller feed into eCatalog API")
    parser.add_argument("--file", required=True, help="Path to CSV feed")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="API base URL")
    args = parser.parse_args()

    with open(args.file, newline="", encoding="utf-8") as feed:
        reader = csv.DictReader(feed)
        for row in reader:
            product = post_json(
                f"{args.base_url}/api/products",
                {
                    "title": row["title"],
                    "brand": row.get("brand") or None,
                    "category": row.get("category") or None,
                    "condition": row["condition"],
                },
            )

            post_json(
                f"{args.base_url}/api/offers",
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

    print("Feed import completed")


if __name__ == "__main__":
    main()
