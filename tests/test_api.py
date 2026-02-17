from pathlib import Path
import io
import json
import unittest
from wsgiref.util import setup_testing_defaults

from apps.api.main import application
from apps.api.repository import (
    create_offer,
    create_product,
    get_comparison,
    get_product_card,
    get_seller_dashboard,
    list_offer_price_history,
    list_offers,
    list_products,
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

    def test_create_product_and_offer_flow_requires_approval_for_comparison(self) -> None:
        product = create_product(
            ProductCreate(title="iPhone 13", brand="Apple", category="phones", condition="used")
        )

        offer = create_offer(
            OfferCreate(
                product_id=product["id"],
                seller=SellerCreate(name="Tech Store", city="Baku"),
                price_azn=1200,
                currency="AZN",
                url="https://example.com/offer/1",
                is_available=True,
            )
        )

        self.assertEqual(offer["status"], "pending")

        with self.assertRaises(ValueError):
            get_comparison(product["id"])

    def test_products_filter_by_condition(self) -> None:
        create_product(
            ProductCreate(title="Samsung A55", brand="Samsung", category="phones", condition="new")
        )
        create_product(
            ProductCreate(title="Lenovo ThinkPad", brand="Lenovo", category="laptops", condition="used")
        )

        filtered = list_products(condition="used", status=None)
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["title"], "Lenovo ThinkPad")

    def test_price_history_tracks_initial_and_updates(self) -> None:
        product = create_product(
            ProductCreate(title="Galaxy S24", brand="Samsung", category="phones", condition="new")
        )
        offer = create_offer(
            OfferCreate(
                product_id=product["id"],
                seller=SellerCreate(name="Mobile Hub", city="Baku"),
                price_azn=1900,
            )
        )

        update_offer_price(offer["id"], 1850)

        history = list_offer_price_history(offer["id"])
        self.assertEqual(len(history), 2)
        self.assertIsNone(history[0]["old_price_azn"])
        self.assertEqual(history[0]["new_price_azn"], 1900)
        self.assertEqual(history[1]["old_price_azn"], 1900)
        self.assertEqual(history[1]["new_price_azn"], 1850)

    def test_seller_dashboard_and_product_card(self) -> None:
        product = create_product(
            ProductCreate(title="PS5", brand="Sony", category="consoles", condition="new")
        )
        offer = create_offer(
            OfferCreate(
                product_id=product["id"],
                seller=SellerCreate(name="ConsoleHouse", city="Baku"),
                price_azn=999,
            )
        )

        card = get_product_card(product["id"])
        self.assertEqual(card["offers_total"], 1)
        self.assertEqual(card["offers_approved"], 0)

        dashboard = get_seller_dashboard("ConsoleHouse")
        self.assertEqual(dashboard["offers_count"], 1)
        self.assertEqual(dashboard["status_counts"]["pending"], 1)
        self.assertEqual(dashboard["price_changes_count"], 1)

        offers = list_offers(seller_name="ConsoleHouse")
        self.assertEqual(len(offers), 1)
        self.assertEqual(offers[0]["id"], offer["id"])


class ApiHttpValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        db = Path("ecatalog.db")
        if db.exists():
            db.unlink()
        init_db()

    def _request(self, method: str, path: str, payload: dict | None = None):
        environ = {}
        setup_testing_defaults(environ)
        environ["REQUEST_METHOD"] = method
        if "?" in path:
            path_info, query_string = path.split("?", 1)
        else:
            path_info, query_string = path, ""

        environ["PATH_INFO"] = path_info
        environ["QUERY_STRING"] = query_string

        body = b""
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

    def test_rejects_invalid_product_title(self) -> None:
        status, body = self._request("POST", "/api/products", {"title": "a", "condition": "new"})
        self.assertTrue(status.startswith("400"))
        self.assertEqual(body["error"], "Invalid title")

    def test_offer_status_patch_flow(self) -> None:
        _, created_product = self._request(
            "POST",
            "/api/products",
            {"title": "PlayStation 5", "brand": "Sony", "category": "consoles", "condition": "new"},
        )

        status, created_offer = self._request(
            "POST",
            "/api/offers",
            {
                "product_id": created_product["id"],
                "seller": {"name": "ConsoleHouse", "city": "Baku"},
                "price_azn": 950,
                "currency": "AZN",
                "url": "https://example.com/ps5",
                "is_available": True,
            },
        )
        self.assertTrue(status.startswith("201"))
        self.assertEqual(created_offer["status"], "pending")

        status, updated_offer = self._request(
            "PATCH", f"/api/offers/{created_offer['id']}/status", {"status": "approved"}
        )
        self.assertTrue(status.startswith("200"))
        self.assertEqual(updated_offer["status"], "approved")

        status, comparison = self._request("GET", f"/api/compare/{created_product['id']}")
        self.assertTrue(status.startswith("200"))
        self.assertEqual(comparison["offers_count"], 1)

    def test_offer_price_update_and_history_endpoint(self) -> None:
        _, created_product = self._request(
            "POST",
            "/api/products",
            {"title": "MacBook Air", "brand": "Apple", "category": "laptops", "condition": "used"},
        )
        _, created_offer = self._request(
            "POST",
            "/api/offers",
            {
                "product_id": created_product["id"],
                "seller": {"name": "Laptop Store", "city": "Baku"},
                "price_azn": 2100,
                "currency": "AZN",
            },
        )

        status, updated_offer = self._request(
            "PATCH", f"/api/offers/{created_offer['id']}/price", {"price_azn": 2050}
        )
        self.assertTrue(status.startswith("200"))
        self.assertEqual(updated_offer["price_azn"], 2050)

        status, history = self._request("GET", f"/api/offers/{created_offer['id']}/price-history")
        self.assertTrue(status.startswith("200"))
        self.assertEqual(len(history), 2)
        self.assertEqual(history[1]["old_price_azn"], 2100)
        self.assertEqual(history[1]["new_price_azn"], 2050)

    def test_product_filters_and_seller_dashboard_endpoint(self) -> None:
        _, p1 = self._request(
            "POST",
            "/api/products",
            {"title": "Dell XPS", "brand": "Dell", "category": "laptops", "condition": "used"},
        )
        _, p2 = self._request(
            "POST",
            "/api/products",
            {"title": "Asus Zenbook", "brand": "Asus", "category": "laptops", "condition": "new"},
        )
        _, o1 = self._request(
            "POST",
            "/api/offers",
            {
                "product_id": p1["id"],
                "seller": {"name": "NotebookHub", "city": "Baku"},
                "price_azn": 1400,
                "currency": "AZN",
            },
        )
        self._request("PATCH", f"/api/offers/{o1['id']}/status", {"status": "approved"})
        _, o2 = self._request(
            "POST",
            "/api/offers",
            {
                "product_id": p2["id"],
                "seller": {"name": "NotebookHub", "city": "Baku"},
                "price_azn": 2200,
                "currency": "AZN",
            },
        )
        self._request("PATCH", f"/api/offers/{o2['id']}/status", {"status": "approved"})

        status, products = self._request(
            "GET", "/api/products?category=laptops&min_price=1300&max_price=2000&city=Baku&status=approved"
        )
        self.assertTrue(status.startswith("200"))
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0]["title"], "Dell XPS")

        status, dashboard = self._request("GET", "/api/sellers/NotebookHub/dashboard")
        self.assertTrue(status.startswith("200"))
        self.assertEqual(dashboard["offers_count"], 2)

        status, card = self._request("GET", f"/api/products/{p1['id']}/card")
        self.assertTrue(status.startswith("200"))
        self.assertEqual(card["offers_approved"], 1)


if __name__ == "__main__":
    unittest.main()
