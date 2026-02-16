import json
from pathlib import Path
from urllib.parse import parse_qs
from wsgiref.simple_server import make_server

from apps.api.repository import create_offer, create_product, get_comparison, list_offers, list_products
from apps.api.schemas import OfferCreate, ProductCreate, SellerCreate, VALID_CONDITIONS
from apps.api.storage import init_db

WEB_DIR = Path(__file__).resolve().parents[1] / "web"


def json_response(start_response, status: str, payload: dict | list):
    body = json.dumps(payload).encode("utf-8")
    start_response(status, [("Content-Type", "application/json"), ("Content-Length", str(len(body)))])
    return [body]


def file_response(start_response, path: Path, content_type: str):
    body = path.read_bytes()
    start_response("200 OK", [("Content-Type", content_type), ("Content-Length", str(len(body)))])
    return [body]


def parse_json_body(environ) -> dict:
    size = int(environ.get("CONTENT_LENGTH", "0") or 0)
    raw = environ["wsgi.input"].read(size)
    return json.loads(raw.decode("utf-8")) if raw else {}


def application(environ, start_response):
    path = environ["PATH_INFO"]
    method = environ["REQUEST_METHOD"]

    if path == "/":
        return file_response(start_response, WEB_DIR / "index.html", "text/html; charset=utf-8")

    if path == "/web/styles.css":
        return file_response(start_response, WEB_DIR / "styles.css", "text/css; charset=utf-8")

    if path == "/web/app.js":
        return file_response(start_response, WEB_DIR / "app.js", "application/javascript; charset=utf-8")

    if path == "/health":
        return json_response(start_response, "200 OK", {"status": "ok"})

    if path == "/api/products" and method == "POST":
        data = parse_json_body(environ)
        if data.get("condition") not in VALID_CONDITIONS:
            return json_response(start_response, "400 Bad Request", {"error": "Invalid condition"})
        payload = ProductCreate(
            title=data["title"],
            brand=data.get("brand"),
            category=data.get("category"),
            condition=data["condition"],
        )
        return json_response(start_response, "201 Created", create_product(payload))

    if path == "/api/products" and method == "GET":
        query = parse_qs(environ.get("QUERY_STRING", ""))
        condition = query.get("condition", [None])[0]
        if condition and condition not in VALID_CONDITIONS:
            return json_response(start_response, "400 Bad Request", {"error": "Invalid condition"})

        data = list_products(
            search=query.get("search", [None])[0],
            category=query.get("category", [None])[0],
            condition=condition,
        )
        return json_response(start_response, "200 OK", data)

    if path == "/api/offers" and method == "POST":
        data = parse_json_body(environ)
        payload = OfferCreate(
            product_id=int(data["product_id"]),
            seller=SellerCreate(
                name=data["seller"]["name"],
                city=data["seller"].get("city"),
            ),
            price_azn=float(data["price_azn"]),
            currency=data.get("currency", "AZN"),
            url=data.get("url"),
            is_available=bool(data.get("is_available", True)),
        )
        return json_response(start_response, "201 Created", create_offer(payload))

    if path == "/api/offers" and method == "GET":
        query = parse_qs(environ.get("QUERY_STRING", ""))
        product_id = query.get("product_id", [None])[0]
        data = list_offers(int(product_id)) if product_id else list_offers()
        return json_response(start_response, "200 OK", data)

    if path.startswith("/api/compare/") and method == "GET":
        product_id = int(path.rsplit("/", 1)[-1])
        try:
            result = get_comparison(product_id)
            return json_response(start_response, "200 OK", result)
        except ValueError:
            return json_response(start_response, "404 Not Found", {"error": "Product not found"})

    return json_response(start_response, "404 Not Found", {"error": "Not found"})


def run() -> None:
    init_db()
    with make_server("0.0.0.0", 8000, application) as server:
        print("Serving on http://127.0.0.1:8000")
        server.serve_forever()


if __name__ == "__main__":
    run()
