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


def _offer_row(cur, offer_id: int):
    return cur.execute(
        """
        SELECT o.id, p.id as product_id, p.title, s.name as seller_name, s.city as seller_city,
               s.verification_level, s.rating as seller_rating, s.review_count,
               o.price_azn, o.currency, p.condition, o.is_available, o.url, o.status
        FROM offers o
        JOIN products p ON p.id = o.product_id
        JOIN sellers s ON s.id = o.seller_id
        WHERE o.id = ?
        """,
        (offer_id,),
    ).fetchone()


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

    row = _offer_row(cur, offer_id)
    conn.close()
    data = dict(row)
    data["is_available"] = bool(data["is_available"])
    return data


def update_offer_status(offer_id: int, status: str) -> dict:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE offers SET status = ? WHERE id = ?", (status, offer_id))
    conn.commit()

    row = _offer_row(cur, offer_id)
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

    row = _offer_row(cur, offer_id)
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
               s.verification_level, s.rating as seller_rating, s.review_count,
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


def set_seller_verification(seller_name: str, level: str) -> dict:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE sellers SET verification_level = ? WHERE LOWER(name) = ?",
        (level, seller_name.lower()),
    )
    conn.commit()

    seller = cur.execute(
        "SELECT id, name, city, rating, verification_level, review_count FROM sellers WHERE LOWER(name) = ? ORDER BY id DESC LIMIT 1",
        (seller_name.lower(),),
    ).fetchone()
    conn.close()

    if not seller:
        raise ValueError("Seller not found")

    return dict(seller)


def add_seller_review(seller_name: str, reviewer_name: str, score: int, comment: str | None) -> dict:
    conn = get_connection()
    cur = conn.cursor()

    seller = cur.execute(
        "SELECT id, name FROM sellers WHERE LOWER(name) = ? ORDER BY id DESC LIMIT 1",
        (seller_name.lower(),),
    ).fetchone()
    if not seller:
        conn.close()
        raise ValueError("Seller not found")

    cur.execute(
        "INSERT INTO seller_reviews (seller_id, reviewer_name, score, comment) VALUES (?, ?, ?, ?)",
        (seller["id"], reviewer_name, score, comment),
    )

    agg = cur.execute(
        "SELECT ROUND(AVG(score), 2) AS avg_score, COUNT(*) AS count_reviews FROM seller_reviews WHERE seller_id = ?",
        (seller["id"],),
    ).fetchone()

    cur.execute(
        "UPDATE sellers SET rating = ?, review_count = ? WHERE id = ?",
        (float(agg["avg_score"]), int(agg["count_reviews"]), seller["id"]),
    )

    review_id = cur.lastrowid
    conn.commit()

    review = cur.execute(
        "SELECT id, reviewer_name, score, comment, created_at FROM seller_reviews WHERE id = ?",
        (review_id,),
    ).fetchone()

    seller_state = cur.execute(
        "SELECT id, name, city, rating, verification_level, review_count FROM sellers WHERE id = ?",
        (seller["id"],),
    ).fetchone()

    conn.close()
    return {"review": dict(review), "seller": dict(seller_state)}


def list_seller_reviews(seller_name: str) -> list[dict]:
    conn = get_connection()
    cur = conn.cursor()

    seller = cur.execute(
        "SELECT id FROM sellers WHERE LOWER(name) = ? ORDER BY id DESC LIMIT 1",
        (seller_name.lower(),),
    ).fetchone()
    if not seller:
        conn.close()
        raise ValueError("Seller not found")

    rows = cur.execute(
        "SELECT id, reviewer_name, score, comment, created_at FROM seller_reviews WHERE seller_id = ? ORDER BY id DESC",
        (seller["id"],),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def create_price_alert(product_id: int, target_price_azn: float, contact_email: str) -> dict:
    if not product_exists(product_id):
        raise ValueError("Product does not exist")

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO price_alerts (product_id, target_price_azn, contact_email) VALUES (?, ?, ?)",
        (product_id, target_price_azn, contact_email.lower()),
    )
    conn.commit()
    alert_id = cur.lastrowid

    row = cur.execute(
        "SELECT id, product_id, target_price_azn, contact_email, is_active, created_at FROM price_alerts WHERE id = ?",
        (alert_id,),
    ).fetchone()
    conn.close()
    data = dict(row)
    data["is_active"] = bool(data["is_active"])
    return data


def list_price_alerts(contact_email: str | None = None) -> list[dict]:
    conn = get_connection()
    cur = conn.cursor()

    if contact_email:
        rows = cur.execute(
            "SELECT id, product_id, target_price_azn, contact_email, is_active, created_at FROM price_alerts WHERE contact_email = ? ORDER BY id DESC",
            (contact_email.lower(),),
        ).fetchall()
    else:
        rows = cur.execute(
            "SELECT id, product_id, target_price_azn, contact_email, is_active, created_at FROM price_alerts ORDER BY id DESC"
        ).fetchall()

    conn.close()
    alerts = []
    for row in rows:
        data = dict(row)
        data["is_active"] = bool(data["is_active"])
        alerts.append(data)
    return alerts


def create_fraud_signal(
    *,
    offer_id: int | None,
    seller_name: str | None,
    signal_type: str,
    risk_score: float,
    details: str | None,
) -> dict:
    conn = get_connection()
    cur = conn.cursor()

    seller_id = None
    if seller_name:
        seller = cur.execute(
            "SELECT id FROM sellers WHERE LOWER(name) = ? ORDER BY id DESC LIMIT 1",
            (seller_name.lower(),),
        ).fetchone()
        if not seller:
            conn.close()
            raise ValueError("Seller not found")
        seller_id = seller["id"]

    cur.execute(
        "INSERT INTO fraud_signals (offer_id, seller_id, signal_type, risk_score, details) VALUES (?, ?, ?, ?, ?)",
        (offer_id, seller_id, signal_type, risk_score, details),
    )
    conn.commit()
    signal_id = cur.lastrowid

    row = cur.execute(
        """
        SELECT fs.id, fs.offer_id, fs.signal_type, fs.risk_score, fs.details, fs.created_at,
               s.name AS seller_name
        FROM fraud_signals fs
        LEFT JOIN sellers s ON s.id = fs.seller_id
        WHERE fs.id = ?
        """,
        (signal_id,),
    ).fetchone()
    conn.close()
    return dict(row)




def process_price_alerts() -> dict:
    conn = get_connection()
    cur = conn.cursor()

    rows = cur.execute(
        """
        SELECT pa.id, pa.product_id, pa.target_price_azn, pa.contact_email,
               MIN(o.price_azn) AS best_price
        FROM price_alerts pa
        LEFT JOIN offers o ON o.product_id = pa.product_id AND o.status = 'approved'
        WHERE pa.is_active = 1
        GROUP BY pa.id, pa.product_id, pa.target_price_azn, pa.contact_email
        """
    ).fetchall()

    triggered: list[dict] = []
    checked = 0
    for row in rows:
        checked += 1
        best_price = row["best_price"]
        if best_price is None:
            continue
        if float(best_price) <= float(row["target_price_azn"]):
            cur.execute("UPDATE price_alerts SET is_active = 0 WHERE id = ?", (row["id"],))
            triggered.append(
                {
                    "alert_id": row["id"],
                    "product_id": row["product_id"],
                    "target_price_azn": row["target_price_azn"],
                    "best_price_azn": float(best_price),
                    "contact_email": row["contact_email"],
                }
            )

    conn.commit()
    conn.close()
    return {"checked": checked, "triggered_count": len(triggered), "triggered": triggered}


def auto_scan_fraud_signals(*, min_drop_ratio: float = 0.35, min_risk: float = 0.6) -> dict:
    conn = get_connection()
    cur = conn.cursor()

    offers = cur.execute(
        """
        SELECT o.id AS offer_id, o.price_azn, o.product_id, s.id AS seller_id, s.name AS seller_name,
               AVG(o2.price_azn) AS market_avg
        FROM offers o
        JOIN sellers s ON s.id = o.seller_id
        LEFT JOIN offers o2 ON o2.product_id = o.product_id AND o2.status = 'approved'
        WHERE o.status = 'approved'
        GROUP BY o.id, o.price_azn, o.product_id, s.id, s.name
        """
    ).fetchall()

    created = []
    for row in offers:
        market_avg = row["market_avg"]
        if market_avg is None or market_avg <= 0:
            continue
        drop_ratio = (float(market_avg) - float(row["price_azn"])) / float(market_avg)
        if drop_ratio >= min_drop_ratio:
            risk_score = max(min(drop_ratio, 1.0), min_risk)
            signal_type = "suspicious_price_drop"
            exists = cur.execute(
                """
                SELECT id FROM fraud_signals
                WHERE offer_id = ? AND signal_type = ?
                ORDER BY id DESC LIMIT 1
                """,
                (row["offer_id"], signal_type),
            ).fetchone()
            if exists:
                continue

            details = f"Price drop ratio={drop_ratio:.2f}, market_avg={float(market_avg):.2f}, offer_price={float(row['price_azn']):.2f}"
            cur.execute(
                "INSERT INTO fraud_signals (offer_id, seller_id, signal_type, risk_score, details) VALUES (?, ?, ?, ?, ?)",
                (row["offer_id"], row["seller_id"], signal_type, float(risk_score), details),
            )
            created.append(
                {
                    "offer_id": row["offer_id"],
                    "seller_name": row["seller_name"],
                    "risk_score": float(risk_score),
                }
            )

    conn.commit()
    conn.close()
    return {"scanned_offers": len(offers), "created_signals": len(created), "signals": created}

def list_fraud_signals(min_risk_score: float | None = None) -> list[dict]:
    conn = get_connection()
    cur = conn.cursor()

    if min_risk_score is None:
        rows = cur.execute(
            """
            SELECT fs.id, fs.offer_id, fs.signal_type, fs.risk_score, fs.details, fs.created_at,
                   s.name AS seller_name
            FROM fraud_signals fs
            LEFT JOIN sellers s ON s.id = fs.seller_id
            ORDER BY fs.id DESC
            """
        ).fetchall()
    else:
        rows = cur.execute(
            """
            SELECT fs.id, fs.offer_id, fs.signal_type, fs.risk_score, fs.details, fs.created_at,
                   s.name AS seller_name
            FROM fraud_signals fs
            LEFT JOIN sellers s ON s.id = fs.seller_id
            WHERE fs.risk_score >= ?
            ORDER BY fs.id DESC
            """,
            (min_risk_score,),
        ).fetchall()

    conn.close()
    return [dict(row) for row in rows]


def get_seller_dashboard(seller_name: str) -> dict:
    conn = get_connection()
    cur = conn.cursor()

    seller = cur.execute(
        "SELECT id, name, city, rating, verification_level, review_count FROM sellers WHERE LOWER(name) = ? ORDER BY id DESC LIMIT 1",
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


def get_diagnostics_snapshot() -> dict:
    conn = get_connection()
    cur = conn.cursor()

    products_count = int(cur.execute("SELECT COUNT(*) AS c FROM products").fetchone()["c"])
    sellers_count = int(cur.execute("SELECT COUNT(*) AS c FROM sellers").fetchone()["c"])
    offers_count = int(cur.execute("SELECT COUNT(*) AS c FROM offers").fetchone()["c"])
    approved_offers = int(cur.execute("SELECT COUNT(*) AS c FROM offers WHERE status = 'approved'").fetchone()["c"])
    pending_offers = int(cur.execute("SELECT COUNT(*) AS c FROM offers WHERE status = 'pending'").fetchone()["c"])
    alerts_count = int(cur.execute("SELECT COUNT(*) AS c FROM price_alerts WHERE is_active = 1").fetchone()["c"])
    reviews_count = int(cur.execute("SELECT COUNT(*) AS c FROM seller_reviews").fetchone()["c"])

    avg_risk_row = cur.execute("SELECT ROUND(AVG(risk_score), 4) AS avg_risk FROM fraud_signals").fetchone()
    avg_risk = avg_risk_row["avg_risk"] if avg_risk_row and avg_risk_row["avg_risk"] is not None else 0

    latest_signals_rows = cur.execute(
        """
        SELECT fs.id, fs.signal_type, fs.risk_score, fs.created_at, s.name AS seller_name
        FROM fraud_signals fs
        LEFT JOIN sellers s ON s.id = fs.seller_id
        ORDER BY fs.id DESC
        LIMIT 5
        """
    ).fetchall()

    conn.close()

    return {
        "products_count": products_count,
        "sellers_count": sellers_count,
        "offers_count": offers_count,
        "approved_offers": approved_offers,
        "pending_offers": pending_offers,
        "active_alerts_count": alerts_count,
        "reviews_count": reviews_count,
        "average_fraud_risk": float(avg_risk),
        "latest_fraud_signals": [dict(row) for row in latest_signals_rows],
    }
