from database.db import get_db


def get_summary_stats(user_id):
    db = get_db()
    try:
        row = db.execute(
            "SELECT COALESCE(SUM(amount), 0) as total, COUNT(*) as cnt "
            "FROM expenses WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        total = row["total"]
        cnt   = row["cnt"]

        top_row = db.execute(
            "SELECT category FROM expenses WHERE user_id = ? "
            "GROUP BY category ORDER BY SUM(amount) DESC LIMIT 1",
            (user_id,),
        ).fetchone()
        top_category = top_row["category"] if top_row else "—"

        return {
            "total_spent":  f"₹{total:,.2f}",
            "tx_count":     cnt,
            "top_category": top_category,
        }
    finally:
        db.close()


def get_recent_transactions(user_id, limit=10):
    db = get_db()
    try:
        rows = db.execute(
            "SELECT date, description, category, amount "
            "FROM expenses WHERE user_id = ? "
            "ORDER BY date DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        return [
            {
                "date":        row["date"],
                "description": row["description"] or "",
                "category":    row["category"],
                "amount":      f"₹{row['amount']:,.2f}",
            }
            for row in rows
        ]
    finally:
        db.close()


def get_category_breakdown(user_id):
    db = get_db()
    try:
        rows = db.execute(
            "SELECT category, SUM(amount) as total "
            "FROM expenses WHERE user_id = ? "
            "GROUP BY category ORDER BY total DESC",
            (user_id,),
        ).fetchall()
        if not rows:
            return []

        grand_total = sum(r["total"] for r in rows)
        cats = [
            {
                "name":   r["category"],
                "amount": f"₹{r['total']:,.2f}",
                "pct":    round(r["total"] / grand_total * 100),
            }
            for r in rows
        ]
        # Absorb rounding remainder into the largest category
        diff = 100 - sum(c["pct"] for c in cats)
        if cats:
            cats[0]["pct"] += diff
        return cats
    finally:
        db.close()
