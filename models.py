import os
from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class Product:
    id: Optional[int]
    name: str
    serial_number: str
    sku: str
    price: float
    qty: int
    category: str
    created_at: str

@dataclass
class InvoiceItem:
    id: Optional[int]
    invoice_id: Optional[int]
    product_id: Optional[int]
    description: str
    serial_number: str
    qty: int
    unit_price: float
    line_total: float

@dataclass
class Invoice:
    id: Optional[int]
    invoice_number: str
    customer_name: str
    customer_phone: str
    subtotal: float
    tax_rate: float
    tax_amount: float
    total: float
    payment_method: str
    notes: str
    created_at: str
    items: list[InvoiceItem]
    discount_type: str = ""       # "percent" or "fixed"
    discount_value: float = 0.0
    discount_amount: float = 0.0
