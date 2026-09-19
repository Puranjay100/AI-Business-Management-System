# AI Business Management System — Implementation Plan

## Top-Level Overview

Build a multi-user, role-based AI Business Management System with:

- **Frontend:** Streamlit (multi-page app)
- **Auth:** `streamlit-authenticator` (Admin / Staff roles, shared single business)
- **Business Logic:** Pure Python classes in `core/` — zero dependency on Streamlit or AI
- **AI Layer:** OpenAI `gpt-4o-mini` called from `ai/insights.py`; API key from `.env`
- **Persistence:** Single SQLite file (`bms.db`) managed via a thin `data/storage.py` wrapper
- **Tests:** `pytest` unit tests for all core logic; all OpenAI calls mocked

### Scope Boundaries
- Single shared business (one set of products, customers, sales for all users)
- Two roles: **Admin** (full CRUD + settings + insights) and **Staff** (record sales + view inventory)
- No refund/return workflow in v1
- No multi-currency; one currency set by Admin
- Sales records are immutable (no delete); products/customers are soft-deleted

---

## Project / Folder Structure

```
P_BMS/
├── app.py                          # Streamlit entry point; navigation + auth gate
├── .env                            # OPENAI_API_KEY (never committed)
├── .env.example                    # Template for .env (committed)
├── .gitignore
├── requirements.txt
├── bms.db                          # SQLite database (auto-created on first run)
│
├── core/                           # Pure business logic — no Streamlit, no AI
│   ├── __init__.py
│   ├── models.py                   # Dataclasses: Business, Product, Customer, Sale, User
│   ├── inventory_manager.py        # CRUD + low-stock queries for products
│   ├── customer_manager.py         # CRUD for customers
│   └── sales_manager.py            # Record sales, revenue stats, rankings
│
├── ai/                             # AI/Insights layer
│   ├── __init__.py
│   └── insights.py                 # InsightsEngine: build prompt, call OpenAI, return text
│
├── data/                           # Data persistence layer
│   ├── __init__.py
│   └── storage.py                  # SQLite schema init, CRUD helpers, query helpers
│
├── auth/                           # Authentication layer
│   ├── __init__.py
│   └── auth_manager.py             # Wraps streamlit-authenticator; role lookup
│
├── ui/                             # Streamlit page modules
│   ├── __init__.py
│   ├── page_dashboard.py           # KPI overview (Admin + Staff)
│   ├── page_inventory.py           # Product list, add/edit/archive (Admin only for edit)
│   ├── page_customers.py           # Customer list, add/edit/archive (Admin only)
│   ├── page_sales.py               # Record sale + sales history table/filter
│   ├── page_insights.py            # AI insight generation panel (Admin only)
│   └── page_settings.py            # Business profile + user management (Admin only)
│
├── utils/
│   ├── __init__.py
│   └── formatters.py               # Currency formatting, date helpers
│
├── exceptions.py                   # All custom exception classes
│
└── tests/
    ├── __init__.py
    ├── test_models.py
    ├── test_inventory_manager.py
    ├── test_customer_manager.py
    ├── test_sales_manager.py
    ├── test_storage.py
    └── test_insights.py            # Mocks OpenAI; tests prompt building only
```

---

## Build Order

Build bottom-up: data → models → exceptions → core logic → AI → auth → UI → tests run throughout.

| Step | Module/File | Why This Order |
|---|---|---|
| 1 | `exceptions.py` | All other layers import from here first |
| 2 | `core/models.py` | Dataclasses used by every other module |
| 3 | `data/storage.py` | DB schema + helpers; managers depend on this |
| 4 | `core/inventory_manager.py` | No dependency on sales or customers |
| 5 | `core/customer_manager.py` | No dependency on sales or inventory |
| 6 | `core/sales_manager.py` | Depends on both Product and Customer existing |
| 7 | `ai/insights.py` | Consumes aggregated output of sales_manager |
| 8 | `auth/auth_manager.py` | Wraps streamlit-authenticator; needed by UI |
| 9 | `utils/formatters.py` | Small helpers; needed by UI pages |
| 10 | `ui/page_settings.py` | Business profile setup — must exist before other pages work |
| 11 | `ui/page_inventory.py` | Products must exist before sales |
| 12 | `ui/page_customers.py` | Customers must exist before sales |
| 13 | `ui/page_sales.py` | Depends on products and customers |
| 14 | `ui/page_dashboard.py` | Aggregates data from all managers |
| 15 | `ui/page_insights.py` | Depends on InsightsEngine + aggregated data |
| 16 | `app.py` | Wires navigation + auth; built last |

---

## Layer Definitions

### Core Business Logic Layer (`core/`)
- **What lives here:** Models, all CRUD operations, stock mutation, revenue calculations, rankings
- **What does NOT live here:** Streamlit widgets, OpenAI calls, SQL queries (delegated to `data/storage.py`)
- **Dependency rule:** Imports only from `exceptions.py`, `core/models.py`, `data/storage.py`

### AI/Insights Layer (`ai/`)
- **What lives here:** Prompt construction, OpenAI API call, response parsing
- **What does NOT live here:** Business rules, UI rendering, direct DB access
- **Dependency rule:** Receives pre-aggregated Python dicts/lists from `SalesManager`; never touches raw DB

### UI Layer (`ui/`)
- **What lives here:** Streamlit widgets, form validation messages, page layout
- **What does NOT live here:** Business rules, direct DB access, OpenAI calls
- **Dependency rule:** Calls manager methods and `InsightsEngine`; never touches `storage.py` directly

---

## Public Interfaces (Method Signatures)

### `exceptions.py`
```python
class BmsBaseError(Exception): ...
class ProductNotFoundError(BmsBaseError): ...
class CustomerNotFoundError(BmsBaseError): ...
class SaleNotFoundError(BmsBaseError): ...
class InsufficientStockError(BmsBaseError): ...
class InvalidPriceError(BmsBaseError): ...
class InvalidQuantityError(BmsBaseError): ...
class DuplicateProductError(BmsBaseError): ...
class ValidationError(BmsBaseError): ...
class UnauthorizedError(BmsBaseError): ...
```

### `core/models.py`
```python
@dataclass
class Business:
    name: str
    owner: str
    currency: str          # ISO-4217 3-letter code e.g. "USD"
    low_stock_threshold: int = 5

@dataclass
class Product:
    product_id: str        # UUID
    name: str
    price: float
    quantity_in_stock: int
    category: str
    is_archived: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class Customer:
    customer_id: str       # UUID
    name: str
    email: str = ""
    phone: str = ""
    is_archived: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class Sale:
    sale_id: str           # UUID
    product_id: str
    quantity_sold: int
    unit_price_at_sale: float
    total_amount: float    # computed: quantity_sold * unit_price_at_sale
    sale_date: datetime
    customer_id: str | None = None   # None = walk-in
    notes: str = ""

@dataclass
class User:
    user_id: str
    username: str
    role: str              # "admin" | "staff"
```

### `data/storage.py`
```python
class Storage:
    def __init__(self, db_path: str = "bms.db") -> None: ...
    def init_schema(self) -> None: ...

    # Business
    def save_business(self, business: Business) -> None: ...
    def load_business(self) -> Business | None: ...

    # Products
    def insert_product(self, product: Product) -> None: ...
    def update_product(self, product: Product) -> None: ...
    def fetch_product(self, product_id: str) -> Product | None: ...
    def fetch_all_products(self, include_archived: bool = False) -> list[Product]: ...

    # Customers
    def insert_customer(self, customer: Customer) -> None: ...
    def update_customer(self, customer: Customer) -> None: ...
    def fetch_customer(self, customer_id: str) -> Customer | None: ...
    def fetch_all_customers(self, include_archived: bool = False) -> list[Customer]: ...

    # Sales
    def insert_sale(self, sale: Sale) -> None: ...
    def fetch_sale(self, sale_id: str) -> Sale | None: ...
    def fetch_all_sales(self) -> list[Sale]: ...
    def fetch_sales_in_range(self, start: datetime, end: datetime) -> list[Sale]: ...
```

### `core/inventory_manager.py`
```python
class InventoryManager:
    def __init__(self, storage: Storage) -> None: ...
    def add_product(self, name: str, price: float, quantity: int, category: str) -> Product: ...
    def edit_product(self, product_id: str, name: str, price: float, quantity: int, category: str) -> Product: ...
    def archive_product(self, product_id: str) -> None: ...
    def get_product(self, product_id: str) -> Product: ...
    def list_products(self, include_archived: bool = False) -> list[Product]: ...
    def get_low_stock_products(self, threshold: int | None = None) -> list[Product]: ...
    def search_products(self, query: str) -> list[Product]: ...
    def decrement_stock(self, product_id: str, quantity: int) -> None: ...
```

### `core/customer_manager.py`
```python
class CustomerManager:
    def __init__(self, storage: Storage) -> None: ...
    def add_customer(self, name: str, email: str = "", phone: str = "") -> Customer: ...
    def edit_customer(self, customer_id: str, name: str, email: str, phone: str) -> Customer: ...
    def archive_customer(self, customer_id: str) -> None: ...
    def get_customer(self, customer_id: str) -> Customer: ...
    def list_customers(self, include_archived: bool = False) -> list[Customer]: ...
```

### `core/sales_manager.py`
```python
class SalesManager:
    def __init__(self, storage: Storage, inventory: InventoryManager) -> None: ...
    def record_sale(
        self,
        product_id: str,
        quantity: int,
        sale_date: datetime,
        customer_id: str | None = None,
        notes: str = ""
    ) -> Sale: ...
    def list_sales(self) -> list[Sale]: ...
    def filter_sales(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        product_id: str | None = None,
    ) -> list[Sale]: ...
    def total_revenue(self, start_date: datetime | None = None, end_date: datetime | None = None) -> float: ...
    def best_selling_products(self, top_n: int = 5) -> list[dict]: ...
    def top_customers(self, top_n: int = 5) -> list[dict]: ...
    def sales_by_category(self) -> dict[str, float]: ...
```

### `ai/insights.py`
```python
class InsightsEngine:
    def __init__(self, api_key: str, model: str = "gpt-4o-mini") -> None: ...
    def build_prompt(
        self,
        business: Business,
        revenue_summary: dict,
        best_sellers: list[dict],
        top_customers: list[dict],
        category_breakdown: dict[str, float],
        low_stock: list[Product],
    ) -> str: ...
    def get_insights(self, prompt: str) -> str: ...  # raises if API unavailable
```

### `auth/auth_manager.py`
```python
class AuthManager:
    def __init__(self, credentials_path: str = "credentials.yaml") -> None: ...
    def render_login_widget(self) -> tuple[str | None, bool, str | None]: ...
    # Returns: (name, authentication_status, username)
    def get_role(self, username: str) -> str: ...   # "admin" | "staff"
    def is_admin(self, username: str) -> bool: ...
```

### `utils/formatters.py`
```python
def format_currency(amount: float, currency_code: str) -> str: ...
def format_date(dt: datetime) -> str: ...
def validate_email(email: str) -> bool: ...
def validate_phone(phone: str) -> bool: ...
def validate_currency_code(code: str) -> bool: ...
```

---

## Data Persistence — SQLite

### Why SQLite over JSON/CSV

| Factor | JSON/CSV | SQLite |
|---|---|---|
| Date-range filtering | Load all records into memory, filter in Python | Native `WHERE sale_date BETWEEN` |
| Multi-table joins (product name on sale) | Manual lookups | Native `JOIN` |
| Concurrent writes (multi-user) | Race conditions / file corruption | SQLite handles this safely |
| Setup cost | Zero (stdlib `json`) | Zero (stdlib `sqlite3`) |
| Beginner readability | High | Moderate but well-documented |

**Decision:** SQLite via Python's built-in `sqlite3`. No ORM — raw SQL kept simple and readable. `Storage` class encapsulates all SQL so the rest of the app never writes a query.

### Schema (tables)

```sql
-- business (single row)
CREATE TABLE business (
    name TEXT, owner TEXT, currency TEXT, low_stock_threshold INTEGER
);

-- products
CREATE TABLE products (
    product_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    price REAL NOT NULL,
    quantity_in_stock INTEGER NOT NULL,
    category TEXT NOT NULL,
    is_archived INTEGER DEFAULT 0,
    created_at TEXT NOT NULL
);

-- customers
CREATE TABLE customers (
    customer_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT DEFAULT '',
    phone TEXT DEFAULT '',
    is_archived INTEGER DEFAULT 0,
    created_at TEXT NOT NULL
);

-- sales (immutable — no DELETE)
CREATE TABLE sales (
    sale_id TEXT PRIMARY KEY,
    product_id TEXT NOT NULL,
    customer_id TEXT,
    quantity_sold INTEGER NOT NULL,
    unit_price_at_sale REAL NOT NULL,
    total_amount REAL NOT NULL,
    sale_date TEXT NOT NULL,
    notes TEXT DEFAULT ''
);
```

User credentials are managed separately by `streamlit-authenticator` in `credentials.yaml` (hashed passwords).

---

## AI/LLM Integration Design

### When the AI is called
- Only on the **Insights page**, triggered by a manual "Generate Insights" button click
- Never called automatically or on every page load

### What data is sent
The raw database records are **never sent to OpenAI**. Instead, `SalesManager` computes aggregated stats that are passed to `InsightsEngine.build_prompt()`:

```
revenue_summary:       { "total": 12500.00, "this_month": 3200.00, "last_month": 2800.00 }
best_sellers:          [ { "name": "Widget A", "units_sold": 120, "revenue": 2400.0 }, ... ]
top_customers:         [ { "name": "Acme Corp", "total_spent": 4500.0 }, ... ]
category_breakdown:    { "Electronics": 7000.0, "Clothing": 5500.0 }
low_stock:             [ { "name": "Widget B", "quantity": 2 } ]
```

### Prompt structure
```
System: You are a helpful business analyst. Respond concisely in plain English.
        Keep your response under 200 words.

User:   Business: {name}, Currency: {currency}
        Total revenue all-time: {total}
        Revenue this month: {this_month} vs last month: {last_month}
        Best-selling products: {best_sellers}
        Top customers: {top_customers}
        Sales by category: {category_breakdown}
        Low-stock alerts: {low_stock}

        Please provide:
        1. A 2-sentence trend summary (this month vs last month).
        2. The single best-performing category and why.
        3. One actionable recommendation.
```

### Response handling
- Response is a plain-text string displayed in a `st.info()` box
- No structured parsing needed (plain text is sufficient for v1)
- If the API call fails (network error, invalid key, rate limit), catch the exception and show `st.error("AI insights unavailable: <reason>")` — the rest of the app continues normally

### API key security
- Stored in `.env`: `OPENAI_API_KEY=sk-...`
- Loaded at startup via `python-dotenv`: `load_dotenv()` in `app.py`
- `.env` is listed in `.gitignore`
- `.env.example` with `OPENAI_API_KEY=your-key-here` is committed instead
- Key is read once and injected into `InsightsEngine.__init__()` — never hard-coded

---

## Validation Rules

These are enforced inside the manager classes **before** any write to storage:

| Field | Rule | Exception |
|---|---|---|
| `product.name` | Non-empty string, stripped, max 100 chars | `ValidationError` |
| `product.price` | Float or int, must be ≥ 0.0 | `InvalidPriceError` |
| `product.quantity_in_stock` | Integer ≥ 0 | `InvalidQuantityError` |
| `product.category` | Non-empty string, stripped | `ValidationError` |
| `product.name + category` | Combination must be unique among active products | `DuplicateProductError` |
| `customer.name` | Non-empty string, stripped, max 100 chars | `ValidationError` |
| `customer.email` | Valid email format if non-empty (regex) | `ValidationError` |
| `customer.phone` | Digits, spaces, `+`, `-` only if non-empty | `ValidationError` |
| `sale.quantity_sold` | Integer ≥ 1 | `InvalidQuantityError` |
| `sale.quantity_sold` | Must not exceed `product.quantity_in_stock` | `InsufficientStockError` |
| `sale.product_id` | Must reference an active (non-archived) product | `ProductNotFoundError` |
| `sale.customer_id` | If provided, must reference an active customer | `CustomerNotFoundError` |
| `sale.sale_date` | Must not be in the future | `ValidationError` |
| `business.currency` | Exactly 3 uppercase letters (ISO-4217) | `ValidationError` |

---

## Test Cases

### `tests/test_models.py`
- `test_sale_total_amount_computed_correctly` — qty × unit_price = total_amount
- `test_product_defaults` — is_archived defaults to False
- `test_customer_defaults` — email and phone default to empty string

### `tests/test_inventory_manager.py`
- `test_add_product_success` — valid product is persisted and returned
- `test_add_product_negative_price` — raises `InvalidPriceError`
- `test_add_product_negative_quantity` — raises `InvalidQuantityError`
- `test_add_product_empty_name` — raises `ValidationError`
- `test_add_duplicate_product_name_same_category` — raises `DuplicateProductError`
- `test_add_duplicate_product_name_different_category` — succeeds
- `test_edit_product_updates_fields` — edited fields are persisted
- `test_archive_product_hides_from_list` — archived product not in `list_products()`
- `test_archive_product_still_fetched_with_include_archived` — appears when flag is True
- `test_get_product_not_found` — raises `ProductNotFoundError`
- `test_low_stock_products` — returns only products below threshold
- `test_decrement_stock_success` — stock decreases correctly
- `test_decrement_stock_below_zero` — raises `InsufficientStockError`

### `tests/test_customer_manager.py`
- `test_add_customer_success` — valid customer is persisted
- `test_add_customer_empty_name` — raises `ValidationError`
- `test_add_customer_invalid_email` — raises `ValidationError`
- `test_add_customer_invalid_phone` — raises `ValidationError`
- `test_edit_customer_updates_fields` — edited fields are persisted
- `test_archive_customer_hides_from_list` — archived customer not in default list
- `test_get_customer_not_found` — raises `CustomerNotFoundError`

### `tests/test_sales_manager.py`
- `test_record_sale_success` — sale is persisted; stock is decremented
- `test_record_sale_insufficient_stock` — raises `InsufficientStockError`
- `test_record_sale_zero_quantity` — raises `InvalidQuantityError`
- `test_record_sale_unknown_product` — raises `ProductNotFoundError`
- `test_record_sale_unknown_customer` — raises `CustomerNotFoundError`
- `test_record_sale_walk_in_no_customer` — succeeds with customer_id=None
- `test_record_sale_future_date` — raises `ValidationError`
- `test_total_revenue_all_time` — sum of all sale totals
- `test_total_revenue_date_range` — only sums sales in range
- `test_best_selling_products_ordering` — highest units sold ranked first
- `test_top_customers_ordering` — highest total_spent ranked first
- `test_sales_by_category` — groups revenue by product category

### `tests/test_storage.py`
- `test_init_schema_creates_tables` — all tables exist after init
- `test_insert_and_fetch_product` — round-trip persists all fields
- `test_fetch_product_not_found_returns_none`
- `test_insert_and_fetch_sale` — round-trip persists all fields
- `test_fetch_sales_in_range` — date filter works correctly

### `tests/test_insights.py`
- `test_build_prompt_contains_business_name` — business name is in prompt string
- `test_build_prompt_contains_revenue` — total revenue is in prompt string
- `test_get_insights_calls_openai` — mocks `openai.ChatCompletion.create`; asserts it was called once
- `test_get_insights_returns_response_text` — mock returns dummy text; assert it is returned
- `test_get_insights_api_failure_raises` — mock raises `openai.APIError`; assert exception propagates

---

## Open Questions / Confirmed Assumptions

| # | Item | Status |
|---|---|---|
| OQ-01 | **Single business shared by all users** — one set of products/customers/sales | ✅ Confirmed |
| OQ-02 | **Two roles only:** Admin (full access) and Staff (record sales + view inventory) | ✅ Confirmed |
| OQ-03 | **No login-free access** — streamlit-authenticator blocks the app before any page loads | ✅ Confirmed |
| OQ-04 | **LLM:** OpenAI `gpt-4o-mini`; key in `.env` via `python-dotenv` | ✅ Confirmed |
| OQ-05 | **Storage:** SQLite (`bms.db`), no ORM, raw `sqlite3` | ✅ Confirmed |
| OQ-06 | **Sales are immutable** — no delete; products/customers are soft-deleted (archived) | ✅ Confirmed |
| OQ-07 | **No refund/return workflow** in v1 | ✅ Confirmed |
| OQ-08 | **Single currency** set by Admin in business profile | ✅ Confirmed |
| OQ-09 | **User management** (add/reset Staff accounts) is Admin-only via `page_settings.py` | ✅ Assumed — please confirm |
| OQ-10 | **Walk-in sales** (no linked customer) are allowed — `customer_id` is nullable | ✅ Assumed — please confirm |
| OQ-11 | **Low-stock threshold** is configurable by Admin in business settings (default: 5 units) | ✅ Assumed — please confirm |
| OQ-12 | **Test database** — tests use an in-memory SQLite DB (`:memory:`) so they never touch `bms.db` | ✅ Assumed — standard practice |

---

## Sub-Tasks

### Sub-Task 1 — Foundation: Exceptions, Models, Utils
**Intent:** Create the shared vocabulary (exceptions and dataclasses) that every other module imports.
**Expected Outcomes:** `exceptions.py`, `core/models.py`, `utils/formatters.py` exist and pass `test_models.py`.
**Todo List:**
- [ ] Create `exceptions.py` with all custom exception classes
- [ ] Create `core/models.py` with `Business`, `Product`, `Customer`, `Sale`, `User` dataclasses
- [ ] Create `utils/formatters.py` with `format_currency`, `format_date`, `validate_email`, `validate_phone`, `validate_currency_code`
- [ ] Write `tests/test_models.py` and confirm passing
**Status:** [ ] pending

---

### Sub-Task 2 — Data Layer: Storage
**Intent:** Build the SQLite persistence layer so managers have something to read/write.
**Expected Outcomes:** `data/storage.py` initialises the DB schema and passes all round-trip tests.
**Todo List:**
- [ ] Create `data/storage.py` with `Storage` class and all methods listed in the interfaces section
- [ ] Write `tests/test_storage.py` using `:memory:` SQLite and confirm passing
**Status:** [ ] pending

---

### Sub-Task 3 — Core Logic: InventoryManager
**Intent:** Implement product CRUD, soft-delete, low-stock query, and stock decrement.
**Expected Outcomes:** `core/inventory_manager.py` passes all `test_inventory_manager.py` tests.
**Todo List:**
- [ ] Implement `InventoryManager` with full validation and exception handling
- [ ] Write `tests/test_inventory_manager.py` and confirm all cases pass
**Status:** [ ] pending

---

### Sub-Task 4 — Core Logic: CustomerManager
**Intent:** Implement customer CRUD with soft-delete.
**Expected Outcomes:** `core/customer_manager.py` passes all `test_customer_manager.py` tests.
**Todo List:**
- [ ] Implement `CustomerManager` with full validation and exception handling
- [ ] Write `tests/test_customer_manager.py` and confirm all cases pass
**Status:** [ ] pending

---

### Sub-Task 5 — Core Logic: SalesManager
**Intent:** Implement sale recording (with stock decrement), revenue calculations, and rankings.
**Expected Outcomes:** `core/sales_manager.py` passes all `test_sales_manager.py` tests.
**Todo List:**
- [ ] Implement `SalesManager` with all validation, stock check, and analytics methods
- [ ] Write `tests/test_sales_manager.py` and confirm all cases pass
**Status:** [ ] pending

---

### Sub-Task 6 — AI Layer: InsightsEngine
**Intent:** Build the prompt-construction and OpenAI API call, fully isolated from the rest of the app.
**Expected Outcomes:** `ai/insights.py` passes all `test_insights.py` tests (with mocked OpenAI).
**Todo List:**
- [ ] Create `.env.example`; add `.env` and `bms.db` to `.gitignore`
- [ ] Implement `InsightsEngine` with `build_prompt()` and `get_insights()`
- [ ] Write `tests/test_insights.py` using `unittest.mock.patch` for OpenAI
- [ ] Confirm all tests pass
**Status:** [ ] pending

---

### Sub-Task 7 — Auth Layer: AuthManager
**Intent:** Wrap `streamlit-authenticator` and expose role-aware helpers to the UI.
**Expected Outcomes:** `auth/auth_manager.py` renders login; role lookup works for Admin and Staff.
**Todo List:**
- [ ] Add `streamlit-authenticator` to `requirements.txt`
- [ ] Create `credentials.yaml` template with one Admin and one Staff user (hashed passwords)
- [ ] Implement `AuthManager` with `render_login_widget()`, `get_role()`, `is_admin()`
- [ ] Manual smoke-test login flow in Streamlit
**Status:** [ ] pending

---

### Sub-Task 8 — UI: Settings Page
**Intent:** Business profile setup must exist before any other UI page is useful.
**Expected Outcomes:** Admin can set/edit business name, owner, currency, low-stock threshold.
**Todo List:**
- [ ] Implement `ui/page_settings.py` with a business profile form
- [ ] Add user management section (Admin can add/update Staff accounts in `credentials.yaml`)
- [ ] Enforce Admin-only access via `auth_manager.is_admin()`
**Status:** [ ] pending

---

### Sub-Task 9 — UI: Inventory Page
**Intent:** Allow Admins to add/edit/archive products; Staff to view only.
**Expected Outcomes:** Product table with low-stock highlights; add/edit form for Admins.
**Todo List:**
- [ ] Implement `ui/page_inventory.py` with product table and low-stock warning badges
- [ ] Add/edit form gated to Admin role only
- [ ] Archive button with confirmation gated to Admin role only
**Status:** [ ] pending

---

### Sub-Task 10 — UI: Customers Page
**Intent:** Allow Admins to add/edit/archive customers.
**Expected Outcomes:** Customer table; add/edit form for Admins; Staff see read-only table.
**Todo List:**
- [ ] Implement `ui/page_customers.py` with customer table
- [ ] Add/edit/archive forms gated to Admin role only
**Status:** [ ] pending

---

### Sub-Task 11 — UI: Sales Page
**Intent:** Both roles can record a sale; both roles can view and filter sales history.
**Expected Outcomes:** Sale form; history table with date-range and product filters.
**Todo List:**
- [ ] Implement `ui/page_sales.py` with a sale recording form (product selector, quantity, optional customer, date)
- [ ] Show computed total amount before submission
- [ ] Sales history table with date-range picker and product filter
- [ ] Display revenue total for selected filter
**Status:** [ ] pending

---

### Sub-Task 12 — UI: Dashboard Page
**Intent:** High-level KPI overview accessible to all roles.
**Expected Outcomes:** Metrics cards (total revenue, total sales, top product, low-stock count) and a simple bar chart of sales by category.
**Todo List:**
- [ ] Implement `ui/page_dashboard.py` using `st.metric` and `st.bar_chart`
- [ ] Pull data from `SalesManager` and `InventoryManager`
**Status:** [ ] pending

---

### Sub-Task 13 — UI: Insights Page
**Intent:** Admin-only page to trigger and display the AI-generated insight.
**Expected Outcomes:** "Generate Insights" button calls `InsightsEngine`; result shown in info box; errors shown gracefully.
**Todo List:**
- [ ] Implement `ui/page_insights.py` with the generate button and result display
- [ ] Gate to Admin role only
- [ ] Handle API unavailability with `st.error`
**Status:** [ ] pending

---

### Sub-Task 14 — App Entry Point and Wiring
**Intent:** Wire all pages, auth, and session state into a single navigable Streamlit app.
**Expected Outcomes:** `app.py` loads, login works, navigation shows role-appropriate pages.
**Todo List:**
- [ ] Create `app.py` with `st.sidebar` navigation
- [ ] Call `load_dotenv()` at startup
- [ ] Initialise `Storage`, all managers, and `InsightsEngine` in `st.session_state` once per session
- [ ] Enforce role-based page visibility
- [ ] Create `requirements.txt` with all dependencies
- [ ] Full end-to-end smoke test
**Status:** [ ] pending
