import { describe, expect, it } from "vitest";
import initSqlJs from "sql.js";
import {
  addProduct,
  generateInvoiceNumber,
  initSchema,
  saveInvoice,
  searchInvoices,
  searchProducts,
} from "../db/queries";
import type { Invoice, InvoiceItem, Product } from "../lib/types";

describe("database queries", () => {
  it("adds products and saves invoices with inventory deduction", async () => {
    const SQL = await initSqlJs();
    const db = new SQL.Database() as unknown as Parameters<typeof initSchema>[0];
    initSchema(db);

    const product: Product = {
      id: null,
      name: "Canvas Tote",
      serial_number: "Navy",
      sku: "TOTE-01",
      price: 42,
      qty: 10,
      category: "",
    };
    const id = addProduct(db, product);
    expect(id).toBeGreaterThan(0);

    const found = searchProducts(db, "TOTE");
    expect(found).toHaveLength(1);
    expect(found[0].name).toBe("Canvas Tote");

    const number = generateInvoiceNumber(db);
    expect(number).toBe("INV-786-0001");

    const items: InvoiceItem[] = [
      {
        product_id: id,
        description: "Canvas Tote",
        serial_number: "Navy",
        qty: 2,
        unit_price: 42,
        line_total: 84,
      },
    ];
    const invoice: Invoice = {
      id: null,
      invoice_number: number,
      customer_name: "Sam Rivera",
      customer_phone: "(312) 847-1928",
      customer_email: "sam@example.com",
      subtotal: 84,
      tax_rate: 0.13,
      tax_amount: 10.92,
      total: 94.92,
      payment_method: "Card",
      notes: "",
      created_at: "2026-07-23 12:00:00",
      items,
      discount_type: "",
      discount_value: 0,
      discount_amount: 0,
      discount_timing: "before_tax",
    };
    saveInvoice(db, invoice, items);

    const after = searchProducts(db, "TOTE")[0];
    expect(after.qty).toBe(8);

    const invoices = searchInvoices(db, "Sam");
    expect(invoices).toHaveLength(1);
    expect(invoices[0].items).toHaveLength(1);
  });
});
