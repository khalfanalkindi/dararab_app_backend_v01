#!/usr/bin/env python3
"""
Insert one inventory_inventory row per product: quantity and warehouse_id configurable.

Skips products that already have a row for that warehouse (safe to re-run).

Usage:
  python3 scripts/seed_inventory_all_products_mysql.py --dry-run
  python3 scripts/seed_inventory_all_products_mysql.py
  python3 scripts/seed_inventory_all_products_mysql.py --quantity 500 --warehouse-id 1
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any
from urllib.parse import unquote, urlparse

try:
    import mysql.connector
except ImportError as e:
    print("Install: pip install mysql-connector-python", file=sys.stderr)
    raise e

MYSQL_URL = (
    "mysql://root:DPMCwYKeEPBvcGdQheifhQqICRUuGzBL@mainline.proxy.rlwy.net:29174/railway"
)
MYSQL_HOST = "mainline.proxy.rlwy.net"
MYSQL_PORT = 29174
MYSQL_USER = "root"
MYSQL_PASSWORD = "DPMCwYKeEPBvcGdQheifhQqICRUuGzBL"
MYSQL_DATABASE = "railway"

DEFAULT_WAREHOUSE_ID = 1
DEFAULT_QUANTITY = 1000
CREATED_BY_ID = 4


def _parse_mysql_url(url: str) -> dict[str, Any]:
    url = (url or "").strip()
    if not url:
        return {}
    if url.startswith("mysql+pymysql://"):
        url = "mysql://" + url[len("mysql+pymysql://") :]
    elif url.startswith("mysql2://"):
        url = "mysql://" + url[len("mysql2://") :]
    elif not url.startswith("mysql://"):
        return {}
    u = urlparse(url)
    if not u.hostname:
        return {}
    db = (u.path or "").lstrip("/").split("?", 1)[0]
    return {
        "host": u.hostname,
        "port": int(u.port or 3306),
        "user": unquote(u.username or ""),
        "password": unquote(u.password or ""),
        "database": db,
    }


def _connect_kwargs() -> dict[str, Any]:
    raw = os.environ.get("MYSQL_URL") or os.environ.get("DATABASE_URL") or MYSQL_URL
    p = _parse_mysql_url(str(raw))
    return {
        "host": os.environ.get("MYSQL_HOST") or p.get("host") or MYSQL_HOST,
        "port": int(os.environ.get("MYSQL_PORT") or p.get("port") or MYSQL_PORT),
        "user": os.environ.get("MYSQL_USER") or p.get("user") or MYSQL_USER,
        "password": os.environ.get("MYSQL_PASSWORD") or p.get("password") or MYSQL_PASSWORD,
        "database": os.environ.get("MYSQL_DATABASE") or p.get("database") or MYSQL_DATABASE,
        "charset": "utf8mb4",
        "use_unicode": True,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Seed inventory_inventory for all products.")
    ap.add_argument("--dry-run", action="store_true", help="Rollback after insert.")
    ap.add_argument("--warehouse-id", type=int, default=DEFAULT_WAREHOUSE_ID)
    ap.add_argument("--quantity", type=int, default=DEFAULT_QUANTITY)
    args = ap.parse_args()

    if args.quantity < 0:
        print("--quantity must be >= 0", file=sys.stderr)
        return 1

    created_by = int(os.environ.get("CREATED_BY_ID", str(CREATED_BY_ID)))
    updated_by_raw = os.environ.get("UPDATED_BY_ID", "").strip()
    updated_by = int(updated_by_raw) if updated_by_raw else None

    cnx = mysql.connector.connect(autocommit=False, **_connect_kwargs())
    cur = cnx.cursor()

    try:
        cur.execute("SELECT COUNT(*) FROM inventory_warehouse WHERE id = %s", (args.warehouse_id,))
        wh = int(cur.fetchone()[0])
        if wh != 1:
            print(f"No warehouse with id={args.warehouse_id}. Abort.", file=sys.stderr)
            return 1

        cur.execute("SELECT COUNT(*) FROM inventory_product")
        n_products = int(cur.fetchone()[0])

        cur.execute(
            """
            SELECT COUNT(*) FROM inventory_inventory i
            INNER JOIN inventory_product p ON p.id = i.product_id
            WHERE i.warehouse_id = %s
            """,
            (args.warehouse_id,),
        )
        already = int(cur.fetchone()[0])

        insert_sql = """
            INSERT INTO inventory_inventory (
              created_at, updated_at,
              product_id, warehouse_id, quantity,
              created_by_id, updated_by_id
            )
            SELECT
              SYSDATE(6), SYSDATE(6),
              p.id, %s, %s,
              %s, %s
            FROM inventory_product p
            WHERE NOT EXISTS (
              SELECT 1 FROM inventory_inventory i
              WHERE i.product_id = p.id AND i.warehouse_id = %s
            )
        """
        cur.execute(
            insert_sql,
            (
                args.warehouse_id,
                args.quantity,
                created_by,
                updated_by,
                args.warehouse_id,
            ),
        )
        inserted = cur.rowcount

        if args.dry_run:
            cnx.rollback()
            print(
                f"Dry-run: would insert {inserted} row(s) "
                f"(products total={n_products}, already at warehouse={already}). "
                f"warehouse_id={args.warehouse_id}, quantity={args.quantity}."
            )
        else:
            cnx.commit()
            print(
                f"Inserted {inserted} row(s). "
                f"products total={n_products}, had rows at this warehouse before run={already}. "
                f"warehouse_id={args.warehouse_id}, quantity={args.quantity}."
            )

    except Exception as e:
        cnx.rollback()
        print(f"Rolled back. Error: {e}", file=sys.stderr)
        return 1
    finally:
        cur.close()
        cnx.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
