"""Custom exception hierarchy for the AI Business Management System."""


class BmsBaseError(Exception):
    """Base class for all BMS application errors."""


class ProductNotFoundError(BmsBaseError):
    """Raised when a product ID does not exist or is not accessible."""


class CustomerNotFoundError(BmsBaseError):
    """Raised when a customer ID does not exist or is not accessible."""


class SaleNotFoundError(BmsBaseError):
    """Raised when a sale ID does not exist."""


class InsufficientStockError(BmsBaseError):
    """Raised when a sale quantity exceeds available stock."""


class InvalidPriceError(BmsBaseError):
    """Raised when a price value is negative or otherwise invalid."""


class InvalidQuantityError(BmsBaseError):
    """Raised when a quantity value is zero, negative, or otherwise invalid."""


class DuplicateProductError(BmsBaseError):
    """Raised when a product with the same name and category already exists."""


class ValidationError(BmsBaseError):
    """Raised when a field fails format or business-rule validation."""


class UnauthorizedError(BmsBaseError):
    """Raised when a user attempts an action beyond their role permissions."""
