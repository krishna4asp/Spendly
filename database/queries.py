from datetime import datetime
from database.db import get_db


def _fmt_date(iso):
    try:
        return datetime.strptime(iso, "%Y-%m-%d").strftime("%d %b %Y")
    except (ValueError, TypeError):
        return iso


def _date_clauses(date_from, date_to):
    clauses, params = [], []
    if date_from:
        clauses.append("date >= ?")
        params.append(date_from)
    if date_to:
        clauses.append("date <= ?")
        params.append(date_to)
    return clauses, params


def get_summary_stats(user_id, date_from=None, date_to=None):
    db = get_db()
    try:
        extra, params = _date_clauses(date_from, date_to)
        where = "WHERE user_id = ?" + ("".join(f" AND {c}" for c in extra))
        row = db.execute(
            f"SELECT COALESCE(SUM(amount), 0) as total, COUNT(*) as cnt "
            f"FROM expenses {where}",
            [user_id] + params,
        ).fetchone()
        total = row["total"]
        cnt   = row["cnt"]

        top_row = db.execute(
            f"SELECT category FROM expenses {where} "
            f"GROUP BY category ORDER BY SUM(amount) DESC LIMIT 1",
            [user_id] + params,
        ).fetchone()
        top_category = top_row["category"] if top_row else "—"

        return {
            "total_spent":  f"₹{total:,.2f}",
            "tx_count":     cnt,
            "top_category": top_category,
        }
    finally:
        db.close()


def get_recent_transactions(user_id, limit=10, date_from=None, date_to=None):
    db = get_db()
    try:
        extra, params = _date_clauses(date_from, date_to)
        where = "WHERE user_id = ?" + ("".join(f" AND {c}" for c in extra))
        rows = db.execute(
            f"SELECT date, description, category, amount "
            f"FROM expenses {where} "
            f"ORDER BY date DESC LIMIT ?",
            [user_id] + params + [limit],
        ).fetchall()
        return [
            {
                "date":        _fmt_date(row["date"]),
                "description": row["description"] or "",
                "category":    row["category"],
                "amount":      f"₹{row['amount']:,.2f}",
            }
            for row in rows
        ]
    finally:
        db.close()


def get_category_breakdown(user_id, date_from=None, date_to=None):
    db = get_db()
    try:
        extra, params = _date_clauses(date_from, date_to)
        where = "WHERE user_id = ?" + ("".join(f" AND {c}" for c in extra))
        rows = db.execute(
            f"SELECT category, SUM(amount) as total "
            f"FROM expenses {where} "
            f"GROUP BY category ORDER BY total DESC",
            [user_id] + params,
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
