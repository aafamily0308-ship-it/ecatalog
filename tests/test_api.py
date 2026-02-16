from pathlib import Path
import unittest

from apps.api.repository import create_offer, create_product, get_comparison, list_products
from apps.api.schemas import OfferCreate, ProductCreate, SellerCreate
from apps.api.storage import init_db


class ApiFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        db = Path("ecatalog.db")
        if db.exists():
            db.unlink()
        init_db()

    def test_create_product_and_offer_flow(self) -> None:
        product = create_product(
            ProductCreate(title="iPhone 13", brand="Apple", category="phones", condition="used")
        )

        create_offer(
            OfferCreate(
                product_id=product["id"],
                seller=SellerCreate(name="Tech Store", city="Baku"),
                price_azn=1200,
                currency="AZN",
                url="https://example.com/offer/1",
                is_available=True,
            )
        )

        compare = get_comparison(product["id"])
        self.assertEqual(compare["best_price_azn"], 1200)
        self.assertEqual(compare["offers_count"], 1)

    def test_products_filter_by_condition(self) -> None:
        create_product(
            ProductCreate(title="Samsung A55", brand="Samsung", category="phones", condition="new")
        )
        create_product(
            ProductCreate(title="Lenovo ThinkPad", brand="Lenovo", category="laptops", condition="used")
        )

        filtered = list_products(condition="used")
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["title"], "Lenovo ThinkPad")


if __name__ == "__main__":
    unittest.main()
