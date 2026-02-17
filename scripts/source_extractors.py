import json
from html.parser import HTMLParser


class _JsonLdScriptParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._in_jsonld = False
        self._buffer: list[str] = []
        self.blocks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "script":
            return

        attr_map = {key.lower(): (value or "") for key, value in attrs}
        script_type = attr_map.get("type", "").lower().strip()
        if script_type == "application/ld+json":
            self._in_jsonld = True
            self._buffer = []

    def handle_data(self, data: str) -> None:
        if self._in_jsonld:
            self._buffer.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "script" and self._in_jsonld:
            block = "".join(self._buffer).strip()
            if block:
                self.blocks.append(block)
            self._in_jsonld = False
            self._buffer = []


def _ensure_list(payload: object) -> list[dict]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        if isinstance(payload.get("@graph"), list):
            return [item for item in payload["@graph"] if isinstance(item, dict)]
        return [payload]
    return []


def _normalize_offers(node: dict) -> list[dict]:
    offers = node.get("offers")
    if isinstance(offers, list):
        return [item for item in offers if isinstance(item, dict)]
    if isinstance(offers, dict):
        return [offers]
    return []


def _value_as_float(raw: object) -> float | None:
    if raw is None:
        return None
    try:
        return float(str(raw).replace(",", "."))
    except ValueError:
        return None


def extract_offers_from_jsonld(html: str) -> list[dict]:
    parser = _JsonLdScriptParser()
    parser.feed(html)

    extracted: list[dict] = []

    for block in parser.blocks:
        try:
            payload = json.loads(block)
        except json.JSONDecodeError:
            continue

        for node in _ensure_list(payload):
            node_type = str(node.get("@type", "")).lower()
            if "product" not in node_type:
                continue

            title = node.get("name")
            brand = None
            brand_node = node.get("brand")
            if isinstance(brand_node, dict):
                brand = brand_node.get("name")
            elif isinstance(brand_node, str):
                brand = brand_node

            category = node.get("category")
            offer_nodes = _normalize_offers(node)
            for offer in offer_nodes:
                seller_name = "Unknown seller"
                seller_info = offer.get("seller")
                if isinstance(seller_info, dict) and seller_info.get("name"):
                    seller_name = str(seller_info["name"])

                price = _value_as_float(offer.get("price"))
                if not title or price is None:
                    continue

                condition_raw = str(offer.get("itemCondition", "")).lower()
                if "used" in condition_raw:
                    condition = "used"
                elif "refurb" in condition_raw:
                    condition = "refurbished"
                else:
                    condition = "new"

                extracted.append(
                    {
                        "title": str(title),
                        "brand": str(brand) if brand else None,
                        "category": str(category) if category else None,
                        "condition": condition,
                        "seller_name": seller_name,
                        "seller_city": None,
                        "price_azn": price,
                        "currency": offer.get("priceCurrency") or "AZN",
                        "url": offer.get("url") or node.get("url"),
                    }
                )

    return extracted
