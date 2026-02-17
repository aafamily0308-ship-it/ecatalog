import json
from pathlib import Path
from urllib.parse import parse_qs
from wsgiref.simple_server import make_server

from apps.api.repository import (
    add_seller_review,
    create_fraud_signal,
    create_offer,
    create_price_alert,
    create_product,
    get_comparison,
    get_product_card,
    get_seller_dashboard,
    list_fraud_signals,
    list_offer_price_history,
    list_offers,
    list_price_alerts,
    list_products,
    list_seller_reviews,
    set_seller_verification,
    update_offer_price,
    update_offer_status,
)
from apps.api.schemas import (
    OfferCreate,
    OfferStatusUpdate,
    ProductCreate,
    SellerCreate,
    VALID_CONDITIONS,
    VALID_OFFER_STATUSES,
    VALID_VERIFICATION_LEVELS,
)
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


def _is_valid_text(value: object, *, min_len: int = 2, max_len: int = 200) -> bool:
    if not isinstance(value, str):
        return False
    value = value.strip()
    return min_len <= len(value) <= max_len


def _is_valid_email(value: object) -> bool:
    return isinstance(value, str) and "@" in value and "." in value and len(value) >= 6


def _is_valid_price(value: object) -> bool:
    try:
        return float(value) > 0
    except (ValueError, TypeError):
        return False


def _float_query(raw: str | None, field: str) -> tuple[float | None, str | None]:
    if raw is None:
        return None, None
    try:
        value = float(raw)
    except ValueError:
        return None, f"Invalid {field}"
    if value < 0:
        return None, f"Invalid {field}"
    return value, None


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

        if not _is_valid_text(data.get("title"), min_len=2, max_len=140):
            return json_response(start_response, "400 Bad Request", {"error": "Invalid title"})

        if data.get("brand") and not _is_valid_text(data.get("brand"), min_len=1, max_len=80):
            return json_response(start_response, "400 Bad Request", {"error": "Invalid brand"})

        if data.get("condition") not in VALID_CONDITIONS:
            return json_response(start_response, "400 Bad Request", {"error": "Invalid condition"})

        payload = ProductCreate(
            title=data["title"].strip(),
            brand=data.get("brand").strip() if isinstance(data.get("brand"), str) and data.get("brand").strip() else None,
            category=(
                data.get("category").strip()
                if isinstance(data.get("category"), str) and data.get("category").strip()
                else None
            ),
            condition=data["condition"],
        )
        return json_response(start_response, "201 Created", create_product(payload))

    if path == "/api/products" and method == "GET":
        query = parse_qs(environ.get("QUERY_STRING", ""))
        condition = query.get("condition", [None])[0]
        if condition and condition not in VALID_CONDITIONS:
            return json_response(start_response, "400 Bad Request", {"error": "Invalid condition"})

        min_price, min_error = _float_query(query.get("min_price", [None])[0], "min_price")
        if min_error:
            return json_response(start_response, "400 Bad Request", {"error": min_error})

        max_price, max_error = _float_query(query.get("max_price", [None])[0], "max_price")
        if max_error:
            return json_response(start_response, "400 Bad Request", {"error": max_error})

        status = query.get("status", ["approved"])[0]
        if status and status not in VALID_OFFER_STATUSES:
            return json_response(start_response, "400 Bad Request", {"error": "Invalid offer status"})

        data = list_products(
            search=query.get("search", [None])[0],
            category=query.get("category", [None])[0],
            condition=condition,
            min_price=min_price,
            max_price=max_price,
            city=query.get("city", [None])[0],
            status=status,
        )
        return json_response(start_response, "200 OK", data)

    if path.startswith("/api/products/") and path.endswith("/card") and method == "GET":
        product_id_raw = path.split("/")[3]
        try:
            product_id = int(product_id_raw)
        except ValueError:
            return json_response(start_response, "400 Bad Request", {"error": "Invalid product_id"})
        try:
            return json_response(start_response, "200 OK", get_product_card(product_id))
        except ValueError as exc:
            return json_response(start_response, "404 Not Found", {"error": str(exc)})

    if path == "/api/offers" and method == "POST":
        data = parse_json_body(environ)

        seller = data.get("seller")
        if not isinstance(seller, dict) or not _is_valid_text(seller.get("name"), min_len=2, max_len=120):
            return json_response(start_response, "400 Bad Request", {"error": "Invalid seller"})

        if not isinstance(data.get("product_id"), int) or data["product_id"] <= 0:
            return json_response(start_response, "400 Bad Request", {"error": "Invalid product_id"})

        if not _is_valid_price(data.get("price_azn")):
            return json_response(start_response, "400 Bad Request", {"error": "Invalid price"})

        if data.get("currency") and not _is_valid_text(data.get("currency"), min_len=3, max_len=3):
            return json_response(start_response, "400 Bad Request", {"error": "Invalid currency"})

        payload = OfferCreate(
            product_id=int(data["product_id"]),
            seller=SellerCreate(
                name=seller["name"].strip(),
                city=(seller.get("city").strip() if isinstance(seller.get("city"), str) and seller.get("city").strip() else None),
            ),
            price_azn=float(data["price_azn"]),
            currency=(str(data.get("currency", "AZN")).upper()),
            url=data.get("url"),
            is_available=bool(data.get("is_available", True)),
        )

        try:
            return json_response(start_response, "201 Created", create_offer(payload))
        except ValueError as exc:
            return json_response(start_response, "400 Bad Request", {"error": str(exc)})

    if path == "/api/offers" and method == "GET":
        query = parse_qs(environ.get("QUERY_STRING", ""))
        product_id_raw = query.get("product_id", [None])[0]
        status = query.get("status", [None])[0]

        if status and status not in VALID_OFFER_STATUSES:
            return json_response(start_response, "400 Bad Request", {"error": "Invalid offer status"})

        min_price, min_error = _float_query(query.get("min_price", [None])[0], "min_price")
        if min_error:
            return json_response(start_response, "400 Bad Request", {"error": min_error})

        max_price, max_error = _float_query(query.get("max_price", [None])[0], "max_price")
        if max_error:
            return json_response(start_response, "400 Bad Request", {"error": max_error})

        seller_name = query.get("seller_name", [None])[0]
        city = query.get("city", [None])[0]

        product_id = None
        if product_id_raw:
            try:
                product_id = int(product_id_raw)
            except ValueError:
                return json_response(start_response, "400 Bad Request", {"error": "Invalid product_id"})

        data = list_offers(
            product_id=product_id,
            status=status,
            seller_name=seller_name,
            min_price=min_price,
            max_price=max_price,
            city=city,
        )
        return json_response(start_response, "200 OK", data)

    if path.startswith("/api/offers/") and path.endswith("/status") and method == "PATCH":
        offer_id_raw = path.split("/")[3]
        try:
            offer_id = int(offer_id_raw)
        except ValueError:
            return json_response(start_response, "400 Bad Request", {"error": "Invalid offer id"})

        data = parse_json_body(environ)
        status_update = OfferStatusUpdate(status=data.get("status"))
        if status_update.status not in VALID_OFFER_STATUSES:
            return json_response(start_response, "400 Bad Request", {"error": "Invalid offer status"})

        try:
            return json_response(start_response, "200 OK", update_offer_status(offer_id, status_update.status))
        except ValueError as exc:
            return json_response(start_response, "404 Not Found", {"error": str(exc)})

    if path.startswith("/api/offers/") and path.endswith("/price") and method == "PATCH":
        offer_id_raw = path.split("/")[3]
        try:
            offer_id = int(offer_id_raw)
        except ValueError:
            return json_response(start_response, "400 Bad Request", {"error": "Invalid offer id"})

        data = parse_json_body(environ)
        if not _is_valid_price(data.get("price_azn")):
            return json_response(start_response, "400 Bad Request", {"error": "Invalid price"})

        try:
            return json_response(start_response, "200 OK", update_offer_price(offer_id, float(data["price_azn"])))
        except ValueError as exc:
            return json_response(start_response, "404 Not Found", {"error": str(exc)})

    if path.startswith("/api/offers/") and path.endswith("/price-history") and method == "GET":
        offer_id_raw = path.split("/")[3]
        try:
            offer_id = int(offer_id_raw)
        except ValueError:
            return json_response(start_response, "400 Bad Request", {"error": "Invalid offer id"})

        return json_response(start_response, "200 OK", list_offer_price_history(offer_id))

    if path.startswith("/api/sellers/") and path.endswith("/dashboard") and method == "GET":
        seller_name = path.split("/")[3]
        try:
            return json_response(start_response, "200 OK", get_seller_dashboard(seller_name))
        except ValueError as exc:
            return json_response(start_response, "404 Not Found", {"error": str(exc)})

    if path.startswith("/api/sellers/") and path.endswith("/verify") and method == "PATCH":
        seller_name = path.split("/")[3]
        data = parse_json_body(environ)
        level = data.get("verification_level")
        if level not in VALID_VERIFICATION_LEVELS:
            return json_response(start_response, "400 Bad Request", {"error": "Invalid verification_level"})
        try:
            return json_response(start_response, "200 OK", set_seller_verification(seller_name, level))
        except ValueError as exc:
            return json_response(start_response, "404 Not Found", {"error": str(exc)})

    if path.startswith("/api/sellers/") and path.endswith("/reviews") and method == "POST":
        seller_name = path.split("/")[3]
        data = parse_json_body(environ)
        if not _is_valid_text(data.get("reviewer_name"), min_len=2, max_len=120):
            return json_response(start_response, "400 Bad Request", {"error": "Invalid reviewer_name"})
        score = data.get("score")
        if not isinstance(score, int) or score < 1 or score > 5:
            return json_response(start_response, "400 Bad Request", {"error": "Invalid score"})
        comment = data.get("comment")
        if comment is not None and not isinstance(comment, str):
            return json_response(start_response, "400 Bad Request", {"error": "Invalid comment"})
        try:
            return json_response(
                start_response,
                "201 Created",
                add_seller_review(seller_name, data["reviewer_name"].strip(), score, comment.strip() if isinstance(comment, str) else None),
            )
        except ValueError as exc:
            return json_response(start_response, "404 Not Found", {"error": str(exc)})

    if path.startswith("/api/sellers/") and path.endswith("/reviews") and method == "GET":
        seller_name = path.split("/")[3]
        try:
            return json_response(start_response, "200 OK", list_seller_reviews(seller_name))
        except ValueError as exc:
            return json_response(start_response, "404 Not Found", {"error": str(exc)})

    if path == "/api/alerts" and method == "POST":
        data = parse_json_body(environ)
        if not isinstance(data.get("product_id"), int) or data["product_id"] <= 0:
            return json_response(start_response, "400 Bad Request", {"error": "Invalid product_id"})
        if not _is_valid_price(data.get("target_price_azn")):
            return json_response(start_response, "400 Bad Request", {"error": "Invalid target_price_azn"})
        if not _is_valid_email(data.get("contact_email")):
            return json_response(start_response, "400 Bad Request", {"error": "Invalid contact_email"})
        try:
            return json_response(
                start_response,
                "201 Created",
                create_price_alert(data["product_id"], float(data["target_price_azn"]), data["contact_email"]),
            )
        except ValueError as exc:
            return json_response(start_response, "400 Bad Request", {"error": str(exc)})

    if path == "/api/alerts" and method == "GET":
        query = parse_qs(environ.get("QUERY_STRING", ""))
        email = query.get("contact_email", [None])[0]
        return json_response(start_response, "200 OK", list_price_alerts(email))

    if path == "/api/fraud-signals" and method == "POST":
        data = parse_json_body(environ)
        if not _is_valid_text(data.get("signal_type"), min_len=3, max_len=60):
            return json_response(start_response, "400 Bad Request", {"error": "Invalid signal_type"})
        risk_score = data.get("risk_score")
        try:
            risk_value = float(risk_score)
        except (TypeError, ValueError):
            return json_response(start_response, "400 Bad Request", {"error": "Invalid risk_score"})
        if risk_value < 0 or risk_value > 1:
            return json_response(start_response, "400 Bad Request", {"error": "Invalid risk_score"})

        offer_id = data.get("offer_id")
        if offer_id is not None and (not isinstance(offer_id, int) or offer_id <= 0):
            return json_response(start_response, "400 Bad Request", {"error": "Invalid offer_id"})

        seller_name = data.get("seller_name")
        if seller_name is not None and not _is_valid_text(seller_name, min_len=2, max_len=120):
            return json_response(start_response, "400 Bad Request", {"error": "Invalid seller_name"})

        try:
            return json_response(
                start_response,
                "201 Created",
                create_fraud_signal(
                    offer_id=offer_id,
                    seller_name=seller_name,
                    signal_type=data["signal_type"].strip(),
                    risk_score=risk_value,
                    details=data.get("details"),
                ),
            )
        except ValueError as exc:
            return json_response(start_response, "404 Not Found", {"error": str(exc)})

    if path == "/api/fraud-signals" and method == "GET":
        query = parse_qs(environ.get("QUERY_STRING", ""))
        min_risk, err = _float_query(query.get("min_risk_score", [None])[0], "min_risk_score")
        if err:
            return json_response(start_response, "400 Bad Request", {"error": err})
        return json_response(start_response, "200 OK", list_fraud_signals(min_risk))

    if path.startswith("/api/compare/") and method == "GET":
        product_id_raw = path.rsplit("/", 1)[-1]
        try:
            product_id = int(product_id_raw)
        except ValueError:
            return json_response(start_response, "400 Bad Request", {"error": "Invalid product_id"})

        try:
            result = get_comparison(product_id)
            return json_response(start_response, "200 OK", result)
        except ValueError as exc:
            return json_response(start_response, "404 Not Found", {"error": str(exc)})

    return json_response(start_response, "404 Not Found", {"error": "Not found"})


def run() -> None:
    init_db()
    with make_server("0.0.0.0", 8000, application) as server:
        print("Serving on http://127.0.0.1:8000")
        server.serve_forever()


if __name__ == "__main__":
    run()
