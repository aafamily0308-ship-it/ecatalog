from .schemas import OfferCreate, ProductCreate
from .storage import get_connection


def create_product(payload: ProductCreate) -> dict:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO products (title, brand, category, condition) VALUES (?, ?, ?, ?)",
        (payload.title, payload.brand, payload.category, payload.condition),
    )
    conn.commit()
    product_id = cur.lastrowid
    conn.close()
    return {
        "id": product_id,
        "title": payload.title,
        "brand": payload.brand,
        "category": payload.category,
        "condition": payload.condition,
    }


def product_exists(product_id: int) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    row = cur.execute("SELECT id FROM products WHERE id = ?", (product_id,)).fetchone()
    conn.close()
    return bool(row)


def list_products(
    *,
    search: str | None = None,
    category: str | None = None,
    condition: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    city: str | None = None,
    status: str | None = "approved",
) -> list[dict]:
    conn = get_connection()
    cur = conn.cursor()

    sql = """
        SELECT DISTINCT p.id, p.title, p.brand, p.category, p.condition
        FROM products p
        LEFT JOIN offers o ON o.product_id = p.id
        LEFT JOIN sellers s ON s.id = o.seller_id
        WHERE 1=1
    """
    params: list[object] = []

    if search:
        sql += " AND LOWER(p.title) LIKE ?"
        params.append(f"%{search.lower()}%")

    if category:
        sql += " AND p.category = ?"
        params.append(category)

    if condition:
        sql += " AND p.condition = ?"
        params.append(condition)

    if status:
        sql += " AND (o.status = ? OR o.id IS NULL)"
        params.append(status)

    if min_price is not None:
        sql += " AND (o.price_azn >= ? OR o.id IS NULL)"
        params.append(min_price)

    if max_price is not None:
        sql += " AND (o.price_azn <= ? OR o.id IS NULL)"
        params.append(max_price)

    if city:
        sql += " AND (LOWER(s.city) = ? OR o.id IS NULL)"
        params.append(city.lower())

    sql += " ORDER BY p.id DESC"

    rows = cur.execute(sql, params).fetchall()
    conn.close()

    return [dict(row) for row in rows]


def _find_or_create_seller(name: str, city: str | None) -> int:
    conn = get_connection()
    cur = conn.cursor()
    row = cur.execute("SELECT id FROM sellers WHERE name = ? AND city IS ?", (name, city)).fetchone()
    if row:
        conn.close()
        return row["id"]

    cur.execute("INSERT INTO sellers (name, city) VALUES (?, ?)", (name, city))
    conn.commit()
    seller_id = cur.lastrowid
    conn.close()
    return seller_id


def _insert_price_history(cur, offer_id: int, old_price: float | None, new_price: float) -> None:
    cur.execute(
        "INSERT INTO price_history (offer_id, old_price_azn, new_price_azn) VALUES (?, ?, ?)",
        (offer_id, old_price, new_price),
    )


def create_offer(payload: OfferCreate) -> dict:
    if not product_exists(payload.product_id):
        raise ValueError("Product does not exist")

    seller_id = _find_or_create_seller(payload.seller.name, payload.seller.city)
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO offers (product_id, seller_id, price_azn, currency, url, is_available)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            payload.product_id,
            seller_id,
            payload.price_azn,
            payload.currency,
            payload.url,
            int(payload.is_available),
        ),
    )
    offer_id = cur.lastrowid
    _insert_price_history(cur, offer_id, None, payload.price_azn)
    conn.commit()

    row = cur.execute(
        """
        SELECT o.id, p.id as product_id, p.title, s.name as seller_name, s.city as seller_city,
               o.price_azn, o.currency, p.condition, o.is_available, o.url, o.status
        FROM offers o
        JOIN products p ON p.id = o.product_id
        JOIN sellers s ON s.id = o.seller_id
        WHERE o.id = ?
        """,
        (offer_id,),
    ).fetchone()

    conn.close()
    data = dict(row)
    data["is_available"] = bool(data["is_available"])
    return data


def update_offer_status(offer_id: int, status: str) -> dict:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE offers SET status = ? WHERE id = ?", (status, offer_id))
    conn.commit()

    row = cur.execute(
        """
        SELECT o.id, p.id as product_id, p.title, s.name as seller_name, s.city as seller_city,
               o.price_azn, o.currency, p.condition, o.is_available, o.url, o.status
        FROM offers o
        JOIN products p ON p.id = o.product_id
        JOIN sellers s ON s.id = o.seller_id
        WHERE o.id = ?
        """,
        (offer_id,),
    ).fetchone()
    conn.close()

    if not row:
        raise ValueError("Offer not found")

    data = dict(row)
    data["is_available"] = bool(data["is_available"])
    return data


def update_offer_price(offer_id: int, new_price: float) -> dict:
    conn = get_connection()
    cur = conn.cursor()

    offer = cur.execute("SELECT price_azn FROM offers WHERE id = ?", (offer_id,)).fetchone()
    if not offer:
        conn.close()
        raise ValueError("Offer not found")

    old_price = float(offer["price_azn"])
    cur.execute("UPDATE offers SET price_azn = ? WHERE id = ?", (new_price, offer_id))
    _insert_price_history(cur, offer_id, old_price, new_price)
    conn.commit()

    row = cur.execute(
        """
        SELECT o.id, p.id as product_id, p.title, s.name as seller_name, s.city as seller_city,
               o.price_azn, o.currency, p.condition, o.is_available, o.url, o.status
        FROM offers o
        JOIN products p ON p.id = o.product_id
        JOIN sellers s ON s.id = o.seller_id
        WHERE o.id = ?
        """,
        (offer_id,),
    ).fetchone()
    conn.close()

    data = dict(row)
    data["is_available"] = bool(data["is_available"])
    return data


def list_offer_price_history(offer_id: int) -> list[dict]:
    conn = get_connection()
    cur = conn.cursor()

    rows = cur.execute(
        """
        SELECT id, offer_id, old_price_azn, new_price_azn, changed_at
        FROM price_history
        WHERE offer_id = ?
        ORDER BY id ASC
        """,
        (offer_id,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def list_offers(
    product_id: int | None = None,
    status: str | None = None,
    seller_name: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    city: str | None = None,
) -> list[dict]:
    conn = get_connection()
    cur = conn.cursor()
    sql = """
        SELECT o.id, p.id as product_id, p.title, s.name as seller_name, s.city as seller_city,
               o.price_azn, o.currency, p.condition, o.is_available, o.url, o.status
        FROM offers o
        JOIN products p ON p.id = o.product_id
        JOIN sellers s ON s.id = o.seller_id
    """
    params: list[object] = []
    where_clauses: list[str] = []

    if product_id:
        where_clauses.append("p.id = ?")
        params.append(product_id)

    if status:
        where_clauses.append("o.status = ?")
        params.append(status)

    if seller_name:
        where_clauses.append("LOWER(s.name) = ?")
        params.append(seller_name.lower())

    if min_price is not None:
        where_clauses.append("o.price_azn >= ?")
        params.append(min_price)

    if max_price is not None:
        where_clauses.append("o.price_azn <= ?")
        params.append(max_price)

    if city:
        where_clauses.append("LOWER(s.city) = ?")
        params.append(city.lower())

    if where_clauses:
        sql += " WHERE " + " AND ".join(where_clauses)

    sql += " ORDER BY o.price_azn ASC"

    rows = cur.execute(sql, tuple(params)).fetchall()
    conn.close()

    offers: list[dict] = []
    for row in rows:
        data = dict(row)
        data["is_available"] = bool(data["is_available"])
        offers.append(data)
    return offers


def get_product_card(product_id: int) -> dict:
    conn = get_connection()
    cur = conn.cursor()

    product = cur.execute(
        "SELECT id, title, brand, category, condition FROM products WHERE id = ?",
        (product_id,),
    ).fetchone()
    if not product:
        conn.close()
        raise ValueError("Product not found")

    offers = list_offers(product_id=product_id)
    approved = [offer for offer in offers if offer["status"] == "approved"]

    best_price_approved = min((offer["price_azn"] for offer in approved), default=None)

    conn.close()
    return {
        "product": dict(product),
        "offers_total": len(offers),
        "offers_approved": len(approved),
        "best_price_approved": best_price_approved,
        "offers": offers,
    }


def get_seller_dashboard(seller_name: str) -> dict:
    conn = get_connection()
    cur = conn.cursor()

    seller = cur.execute(
        "SELECT id, name, city, rating FROM sellers WHERE LOWER(name) = ? ORDER BY id DESC LIMIT 1",
        (seller_name.lower(),),
    ).fetchone()
    if not seller:
        conn.close()
        raise ValueError("Seller not found")

    offers = list_offers(seller_name=seller["name"])
    price_rows = cur.execute(
        """
        SELECT COUNT(*) AS changes_count
        FROM price_history ph
        JOIN offers o ON o.id = ph.offer_id
        JOIN sellers s ON s.id = o.seller_id
        WHERE LOWER(s.name) = ?
        """,
        (seller_name.lower(),),
    ).fetchone()

    avg_price = None
    if offers:
        avg_price = round(sum(offer["price_azn"] for offer in offers) / len(offers), 2)

    status_counts = {"pending": 0, "approved": 0, "rejected": 0}
    for offer in offers:
        status_counts[offer["status"]] = status_counts.get(offer["status"], 0) + 1

    conn.close()
    return {
        "seller": dict(seller),
        "offers_count": len(offers),
        "status_counts": status_counts,
        "average_price_azn": avg_price,
        "price_changes_count": int(price_rows["changes_count"] if price_rows else 0),
        "offers": offers,
    }


def get_comparison(product_id: int) -> dict:
    offers = list_offers(product_id=product_id, status="approved")
    if not offers:
        raise ValueError("Product not found or no approved offers available")

    best_price = min(offer["price_azn"] for offer in offers)
    title = offers[0]["title"]

    return {
        "product_id": product_id,
        "title": title,
        "best_price_azn": best_price,
        "offers_count": len(offers),
        "offers": offers,
    }
