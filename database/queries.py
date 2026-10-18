from datetime import datetime
from database.db import get_db


def _fmt_date(iso):
    try:
        return datetime.strptime(iso, "%Y-%m-%d").strftime("%d %b %Y")
    except (ValueError, TypeError):
        return iso


def _build_where(user_id, date_from, date_to):
    clauses = ["user_id = ?"]
    params  = [user_id]
    if date_from:
        clauses.append("date >= ?")
        params.append(date_from)
    if date_to:
        clauses.append("date <= ?")
        params.append(date_to)
    return "WHERE " + " AND ".join(clauses), params


def get_summary_stats(user_id, date_from=None, date_to=None):
    db = get_db()
    try:
        where, params = _build_where(user_id, date_from, date_to)
        row = db.execute(
            "SELECT COALESCE(SUM(amount), 0) as total, COUNT(*) as cnt "
            "FROM expenses " + where,
            params,
        ).fetchone()
        total = row["total"]
        cnt   = row["cnt"]

        top_row = db.execute(
            "SELECT category FROM expenses " + where + " "
            "GROUP BY category ORDER BY SUM(amount) DESC LIMIT 1",
            params,
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
        where, params = _build_where(user_id, date_from, date_to)
        rows = db.execute(
            "SELECT date, description, category, amount "
            "FROM expenses " + where + " "
            "ORDER BY date DESC LIMIT ?",
            params + [limit],
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
        where, params = _build_where(user_id, date_from, date_to)
        rows = db.execute(
            "SELECT category, SUM(amount) as total "
            "FROM expenses " + where + " "
            "GROUP BY category ORDER BY total DESC",
            params,
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
