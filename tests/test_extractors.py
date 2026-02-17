import unittest

from scripts.source_extractors import extract_offers_from_jsonld


class JsonLdExtractorTests(unittest.TestCase):
    def test_extract_product_offer(self) -> None:
        html = """
        <html><head>
          <script type="application/ld+json">
            {
              "@context": "https://schema.org",
              "@type": "Product",
              "name": "iPhone 13 128GB",
              "brand": {"@type": "Brand", "name": "Apple"},
              "category": "phones",
              "offers": {
                "@type": "Offer",
                "price": "1299.99",
                "priceCurrency": "AZN",
                "itemCondition": "https://schema.org/UsedCondition",
                "url": "https://shop.example/iphone13",
                "seller": {"@type": "Organization", "name": "Shop A"}
              }
            }
          </script>
        </head></html>
        """

        rows = extract_offers_from_jsonld(html)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["title"], "iPhone 13 128GB")
        self.assertEqual(row["brand"], "Apple")
        self.assertEqual(row["condition"], "used")
        self.assertEqual(row["price_azn"], 1299.99)

    def test_ignores_invalid_jsonld(self) -> None:
        html = '<script type="application/ld+json">not-json</script>'
        rows = extract_offers_from_jsonld(html)
        self.assertEqual(rows, [])


if __name__ == "__main__":
    unittest.main()
