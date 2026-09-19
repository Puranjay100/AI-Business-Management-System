"""SQLite persistence layer for the BMS.

All SQL is contained within this module; the rest of the application
never constructs or executes SQL statements directly.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Optional

from core.models import Business, Customer, Product, Sale

_ISO_FMT = "%Y-%m-%dT%H:%M:%S"


def _parse_dt(value: str) -> datetime:
    return datetime.strptime(value, _ISO_FMT)


def _fmt_dt(dt: datetime) -> str:
    return dt.strftime(_ISO_FMT)


class Storage:
    """Thin wrapper around a single SQLite database file.

    Parameters
    ----------
    db_path:
        File-system path to the SQLite database.  Pass ``":memory:"`` for
        an in-memory database (used by tests).
    """

    def __init__(self, db_path: str = "bms.db") -> None:
        self._db_path = db_path
        self._conn: sqlite3.Connection = sqlite3.connect(
            db_path, check_same_thread=False
        )
        self._conn.row_factory = sqlite3.Row
        self.init_schema()

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def init_schema(self) -> None:
        """Create tables if they do not exist yet."""
        cur = self._conn.cursor()
        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS business (
                id                  INTEGER PRIMARY KEY DEFAULT 1,
                name                TEXT NOT NULL,
                owner               TEXT NOT NULL,
                currency            TEXT NOT NULL,
                low_stock_threshold INTEGER NOT NULL DEFAULT 5,
                CHECK (id = 1)          -- enforces single row
            );

            CREATE TABLE IF NOT EXISTS products (
                product_id          TEXT PRIMARY KEY,
                name                TEXT NOT NULL,
                price               REAL NOT NULL,
                quantity_in_stock   INTEGER NOT NULL,
                category            TEXT NOT NULL,
                is_archived         INTEGER NOT NULL DEFAULT 0,
                created_at          TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS customers (
                customer_id         TEXT PRIMARY KEY,
                name                TEXT NOT NULL,
                email               TEXT NOT NULL DEFAULT '',
                phone               TEXT NOT NULL DEFAULT '',
                is_archived         INTEGER NOT NULL DEFAULT 0,
                created_at          TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sales (
                sale_id             TEXT PRIMARY KEY,
                product_id          TEXT NOT NULL,
                customer_id         TEXT,
                quantity_sold       INTEGER NOT NULL,
                unit_price_at_sale  REAL NOT NULL,
                total_amount        REAL NOT NULL,
                sale_date           TEXT NOT NULL,
                notes               TEXT NOT NULL DEFAULT ''
            );
            """
        )
        self._conn.commit()

    def close(self) -> None:
        """Close the underlying database connection."""
        self._conn.close()

    # ------------------------------------------------------------------
    # Business profile (single row)
    # ------------------------------------------------------------------

    def save_business(self, business: Business) -> None:
        """Insert or replace the single business row."""
        self._conn.execute(
            """
            INSERT INTO business (id, name, owner, currency, low_stock_threshold)
            VALUES (1, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name                = excluded.name,
                owner               = excluded.owner,
                currency            = excluded.currency,
                low_stock_threshold = excluded.low_stock_threshold
            """,
            (business.name, business.owner, business.currency, business.low_stock_threshold),
        )
        self._conn.commit()

    def load_business(self) -> Optional[Business]:
        """Return the business profile, or *None* if not yet configured."""
        row = self._conn.execute("SELECT * FROM business WHERE id = 1").fetchone()
        if row is None:
            return None
        return Business(
            name=row["name"],
            owner=row["owner"],
            currency=row["currency"],
            low_stock_threshold=row["low_stock_threshold"],
        )

    # ------------------------------------------------------------------
    # Products
    # ------------------------------------------------------------------

    def insert_product(self, product: Product) -> None:
        self._conn.execute(
            """
            INSERT INTO products
                (product_id, name, price, quantity_in_stock, category, is_archived, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                product.product_id,
                product.name,
                product.price,
                product.quantity_in_stock,
                product.category,
                int(product.is_archived),
                _fmt_dt(product.created_at),
            ),
        )
        self._conn.commit()

    def update_product(self, product: Product) -> None:
        self._conn.execute(
            """
            UPDATE products SET
                name              = ?,
                price             = ?,
                quantity_in_stock = ?,
                category          = ?,
                is_archived       = ?
            WHERE product_id = ?
            """,
            (
                product.name,
                product.price,
                product.quantity_in_stock,
                product.category,
                int(product.is_archived),
                product.product_id,
            ),
        )
        self._conn.commit()

    def fetch_product(self, product_id: str) -> Optional[Product]:
        row = self._conn.execute(
            "SELECT * FROM products WHERE product_id = ?", (product_id,)
        ).fetchone()
        if row is None:
            return None
        return self._row_to_product(row)

    def fetch_all_products(self, include_archived: bool = False) -> list[Product]:
        if include_archived:
            rows = self._conn.execute("SELECT * FROM products ORDER BY name").fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM products WHERE is_archived = 0 ORDER BY name"
            ).fetchall()
        return [self._row_to_product(r) for r in rows]

    @staticmethod
    def _row_to_product(row: sqlite3.Row) -> Product:
        return Product(
            product_id=row["product_id"],
            name=row["name"],
            price=row["price"],
            quantity_in_stock=row["quantity_in_stock"],
            category=row["category"],
            is_archived=bool(row["is_archived"]),
            created_at=_parse_dt(row["created_at"]),
        )

    # ------------------------------------------------------------------
    # Customers
    # ------------------------------------------------------------------

    def insert_customer(self, customer: Customer) -> None:
        self._conn.execute(
            """
            INSERT INTO customers
                (customer_id, name, email, phone, is_archived, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                customer.customer_id,
                customer.name,
                customer.email,
                customer.phone,
                int(customer.is_archived),
                _fmt_dt(customer.created_at),
            ),
        )
        self._conn.commit()

    def update_customer(self, customer: Customer) -> None:
        self._conn.execute(
            """
            UPDATE customers SET
                name        = ?,
                email       = ?,
                phone       = ?,
                is_archived = ?
            WHERE customer_id = ?
            """,
            (
                customer.name,
                customer.email,
                customer.phone,
                int(customer.is_archived),
                customer.customer_id,
            ),
        )
        self._conn.commit()

    def fetch_customer(self, customer_id: str) -> Optional[Customer]:
        row = self._conn.execute(
            "SELECT * FROM customers WHERE customer_id = ?", (customer_id,)
        ).fetchone()
        if row is None:
            return None
        return self._row_to_customer(row)

    def fetch_all_customers(self, include_archived: bool = False) -> list[Customer]:
        if include_archived:
            rows = self._conn.execute("SELECT * FROM customers ORDER BY name").fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM customers WHERE is_archived = 0 ORDER BY name"
            ).fetchall()
        return [self._row_to_customer(r) for r in rows]

    @staticmethod
    def _row_to_customer(row: sqlite3.Row) -> Customer:
        return Customer(
            customer_id=row["customer_id"],
            name=row["name"],
            email=row["email"],
            phone=row["phone"],
            is_archived=bool(row["is_archived"]),
            created_at=_parse_dt(row["created_at"]),
        )

    # ------------------------------------------------------------------
    # Sales
    # ------------------------------------------------------------------

    def insert_sale(self, sale: Sale) -> None:
        self._conn.execute(
            """
            INSERT INTO sales
                (sale_id, product_id, customer_id, quantity_sold,
                 unit_price_at_sale, total_amount, sale_date, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                sale.sale_id,
                sale.product_id,
                sale.customer_id,
                sale.quantity_sold,
                sale.unit_price_at_sale,
                sale.total_amount,
                _fmt_dt(sale.sale_date),
                sale.notes,
            ),
        )
        self._conn.commit()

    def fetch_sale(self, sale_id: str) -> Optional[Sale]:
        row = self._conn.execute(
            "SELECT * FROM sales WHERE sale_id = ?", (sale_id,)
        ).fetchone()
        if row is None:
            return None
        return self._row_to_sale(row)

    def fetch_all_sales(self) -> list[Sale]:
        rows = self._conn.execute(
            "SELECT * FROM sales ORDER BY sale_date DESC"
        ).fetchall()
        return [self._row_to_sale(r) for r in rows]

    def fetch_sales_in_range(self, start: datetime, end: datetime) -> list[Sale]:
        rows = self._conn.execute(
            """
            SELECT * FROM sales
            WHERE sale_date BETWEEN ? AND ?
            ORDER BY sale_date DESC
            """,
            (_fmt_dt(start), _fmt_dt(end)),
        ).fetchall()
        return [self._row_to_sale(r) for r in rows]

    @staticmethod
    def _row_to_sale(row: sqlite3.Row) -> Sale:
        return Sale(
            sale_id=row["sale_id"],
            product_id=row["product_id"],
            customer_id=row["customer_id"],
            quantity_sold=row["quantity_sold"],
            unit_price_at_sale=row["unit_price_at_sale"],
            total_amount=row["total_amount"],
            sale_date=_parse_dt(row["sale_date"]),
            notes=row["notes"],
        )
