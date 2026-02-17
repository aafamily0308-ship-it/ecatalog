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
) -> list[dict]:
    conn = get_connection()
    cur = conn.cursor()

    sql = "SELECT id, title, brand, category, condition FROM products WHERE 1=1"
    params: list[object] = []

    if search:
        sql += " AND LOWER(title) LIKE ?"
        params.append(f"%{search.lower()}%")

    if category:
        sql += " AND category = ?"
        params.append(category)

    if condition:
        sql += " AND condition = ?"
        params.append(condition)

    sql += " ORDER BY id DESC"

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
    conn.commit()
    offer_id = cur.lastrowid

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


def list_offers(product_id: int | None = None, status: str | None = None) -> list[dict]:
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


def get_comparison(product_id: int) -> dict:
    offers = list_offers(product_id, status="approved")
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
