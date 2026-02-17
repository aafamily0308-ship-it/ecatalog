from pathlib import Path
import io
import json
import unittest
from wsgiref.util import setup_testing_defaults

from apps.api.main import application
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
    list_price_alerts,
    list_products,
    list_seller_reviews,
    set_seller_verification,
    update_offer_price,
)
from apps.api.schemas import OfferCreate, ProductCreate, SellerCreate
from apps.api.storage import init_db


class ApiFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        db = Path("ecatalog.db")
        if db.exists():
            db.unlink()
        init_db()

    def test_price_history_tracks_initial_and_updates(self) -> None:
        product = create_product(ProductCreate(title="Galaxy S24", brand="Samsung", category="phones", condition="new"))
        offer = create_offer(OfferCreate(product_id=product["id"], seller=SellerCreate(name="Mobile Hub", city="Baku"), price_azn=1900))
        update_offer_price(offer["id"], 1850)
        history = list_offer_price_history(offer["id"])
        self.assertEqual(len(history), 2)
        self.assertIsNone(history[0]["old_price_azn"])
        self.assertEqual(history[1]["new_price_azn"], 1850)

    def test_phase2_trust_and_alerts_repository_flow(self) -> None:
        product = create_product(ProductCreate(title="PS5", brand="Sony", category="consoles", condition="new"))
        create_offer(OfferCreate(product_id=product["id"], seller=SellerCreate(name="ConsoleHouse", city="Baku"), price_azn=1100))

        seller = set_seller_verification("ConsoleHouse", "verified")
        self.assertEqual(seller["verification_level"], "verified")

        review_payload = add_seller_review("ConsoleHouse", "Ali", 5, "Great seller")
        self.assertEqual(review_payload["seller"]["review_count"], 1)
        reviews = list_seller_reviews("ConsoleHouse")
        self.assertEqual(len(reviews), 1)

        alert = create_price_alert(product["id"], 1000, "user@example.com")
        self.assertTrue(alert["is_active"])
        alerts = list_price_alerts("user@example.com")
        self.assertEqual(len(alerts), 1)

        signal = create_fraud_signal(
            offer_id=None,
            seller_name="ConsoleHouse",
            signal_type="suspicious_price",
            risk_score=0.8,
            details="Very low price compared to market",
        )
        self.assertEqual(signal["seller_name"], "ConsoleHouse")
        signals = list_fraud_signals(min_risk_score=0.7)
        self.assertEqual(len(signals), 1)

    def test_dashboard_card_and_compare(self) -> None:
        product = create_product(ProductCreate(title="Dell XPS", brand="Dell", category="laptops", condition="used"))
        offer = create_offer(OfferCreate(product_id=product["id"], seller=SellerCreate(name="NotebookHub", city="Baku"), price_azn=1400))

        with self.assertRaises(ValueError):
            get_comparison(product["id"])

        # approve via HTTP-like helper path not needed, just repository status path omitted here
        card = get_product_card(product["id"])
        self.assertEqual(card["offers_total"], 1)

        dashboard = get_seller_dashboard("NotebookHub")
        self.assertEqual(dashboard["offers_count"], 1)
        self.assertEqual(dashboard["status_counts"]["pending"], 1)
        self.assertEqual(offer["seller_name"], "NotebookHub")


class ApiHttpValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        db = Path("ecatalog.db")
        if db.exists():
            db.unlink()
        init_db()

    def _request(self, method: str, path: str, payload: dict | None = None):
        environ = {}
        setup_testing_defaults(environ)
        if "?" in path:
            path_info, query_string = path.split("?", 1)
        else:
            path_info, query_string = path, ""

        environ["REQUEST_METHOD"] = method
        environ["PATH_INFO"] = path_info
        environ["QUERY_STRING"] = query_string

        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            environ["CONTENT_LENGTH"] = str(len(body))
            environ["wsgi.input"] = io.BytesIO(body)
        else:
            environ["CONTENT_LENGTH"] = "0"
            environ["wsgi.input"] = io.BytesIO(b"")

        captured: dict = {}

        def start_response(status, headers):
            captured["status"] = status
            captured["headers"] = headers

        response_body = b"".join(application(environ, start_response))
        return captured["status"], json.loads(response_body.decode("utf-8"))

    def test_phase2_http_endpoints(self) -> None:
        _, product = self._request("POST", "/api/products", {"title": "iPhone 15", "brand": "Apple", "category": "phones", "condition": "new"})
        _, offer = self._request("POST", "/api/offers", {
            "product_id": product["id"], "seller": {"name": "TechStore", "city": "Baku"}, "price_azn": 2500, "currency": "AZN"
        })

        status, verify = self._request("PATCH", "/api/sellers/TechStore/verify", {"verification_level": "verified"})
        self.assertTrue(status.startswith("200"))
        self.assertEqual(verify["verification_level"], "verified")

        status, review = self._request("POST", "/api/sellers/TechStore/reviews", {"reviewer_name": "Nigar", "score": 4, "comment": "Fast response"})
        self.assertTrue(status.startswith("201"))
        self.assertEqual(review["seller"]["review_count"], 1)

        status, reviews = self._request("GET", "/api/sellers/TechStore/reviews")
        self.assertTrue(status.startswith("200"))
        self.assertEqual(len(reviews), 1)

        status, alert = self._request("POST", "/api/alerts", {"product_id": product["id"], "target_price_azn": 2200, "contact_email": "user@example.com"})
        self.assertTrue(status.startswith("201"))
        self.assertEqual(alert["contact_email"], "user@example.com")

        status, alerts = self._request("GET", "/api/alerts?contact_email=user@example.com")
        self.assertTrue(status.startswith("200"))
        self.assertEqual(len(alerts), 1)

        status, signal = self._request("POST", "/api/fraud-signals", {
            "offer_id": offer["id"], "seller_name": "TechStore", "signal_type": "duplicate_listing", "risk_score": 0.65, "details": "same photos"
        })
        self.assertTrue(status.startswith("201"))
        self.assertEqual(signal["signal_type"], "duplicate_listing")

        status, signals = self._request("GET", "/api/fraud-signals?min_risk_score=0.6")
        self.assertTrue(status.startswith("200"))
        self.assertEqual(len(signals), 1)


if __name__ == "__main__":
    unittest.main()
