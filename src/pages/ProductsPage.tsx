import { useEffect, useState } from "react";
import {
  addProduct,
  deleteProduct,
  searchProducts,
  updateProduct,
  upsertProductBySku,
} from "../db/queries";
import { getDatabase, schedulePersist } from "../db/client";
import { parseProductSpreadsheet } from "../lib/importProducts";
import { formatCurrency } from "../lib/money";
import type { Product } from "../lib/types";
import { EmptyState, SkeletonRows } from "../components/EmptyState";
import { useToast } from "../components/Toast";
import { Button, Dialog, Field, inputClass, inputStyle } from "../components/ui";

const emptyProduct = (): Product => ({
  id: null,
  name: "",
  serial_number: "",
  sku: "",
  price: 0,
  qty: 0,
  category: "",
});

export function ProductsPage() {
  const toast = useToast();
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [products, setProducts] = useState<Product[]>([]);
  const [editorOpen, setEditorOpen] = useState(false);
  const [draft, setDraft] = useState<Product>(emptyProduct());
  const [deleteId, setDeleteId] = useState<number | null>(null);

  function refresh(q = query) {
    const db = getDatabase();
    setProducts(searchProducts(db, q));
    setLoading(false);
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    refresh(query);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query]);

  const lowStock = products.filter((p) => p.qty <= 5);

  function openCreate() {
    setDraft(emptyProduct());
    setEditorOpen(true);
  }

  function openEdit(product: Product) {
    setDraft({ ...product });
    setEditorOpen(true);
  }

  function save(closeAfter: boolean) {
    if (!draft.name.trim()) {
      toast.push("Product name is required", "error");
      return;
    }
    const db = getDatabase();
    const payload: Product = {
      ...draft,
      name: draft.name.trim(),
      sku: draft.sku.trim(),
      serial_number: draft.serial_number.trim(),
      price: Number(draft.price) || 0,
      qty: Number(draft.qty) || 0,
    };
    if (payload.id) {
      updateProduct(db, payload);
      toast.push("Product updated", "success");
    } else {
      addProduct(db, payload);
      toast.push("Product added", "success");
    }
    schedulePersist();
    refresh();
    if (closeAfter) {
      setEditorOpen(false);
    } else {
      setDraft(emptyProduct());
    }
  }

  async function onImportFile(file: File) {
    const buf = await file.arrayBuffer();
    const rows = parseProductSpreadsheet(buf);
    if (!rows.length) {
      toast.push("No product rows found in that file", "error");
      return;
    }
    const db = getDatabase();
    let updated = 0;
    let added = 0;
    for (const row of rows) {
      const existing = searchProducts(db, row.sku).find((p) => p.sku && p.sku === row.sku);
      if (existing && row.sku) {
        upsertProductBySku(db, row);
        updated += 1;
      } else {
        addProduct(db, row);
        added += 1;
      }
    }
    schedulePersist();
    refresh();
    toast.push(`Imported ${added} new, updated ${updated}`, "success");
  }

  return (
    <div className="mx-auto max-w-[1440px]">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <h2 className="text-xl font-semibold tracking-tight">Products</h2>
          <p className="text-sm text-[var(--text-secondary)]">
            Stock list · import a spreadsheet when you need a batch
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="primary" onClick={openCreate}>
            Add product
          </Button>
          <label className="focus-ring inline-flex cursor-pointer items-center justify-center rounded-lg border px-3 py-2 text-base font-semibold transition-all duration-200 ease-[cubic-bezier(0.32,0.72,0,1)] active:scale-[0.98]"
            style={{ background: "var(--surface)", borderColor: "var(--border-strong)", color: "var(--text)" }}
          >
            Import
            <input
              type="file"
              accept=".csv,.xlsx,.xls"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) void onImportFile(file);
                e.target.value = "";
              }}
            />
          </label>
          <a
            className="focus-ring inline-flex items-center rounded-lg px-3 py-2 text-sm font-semibold text-[var(--accent)]"
            href="./templates/product_import_template.csv"
            download
          >
            Template
          </a>
        </div>
      </div>

      <div className="mt-3">
        <Field label="Search products">
          <input
            className={inputClass}
            style={inputStyle()}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Name, SKU, or details"
          />
        </Field>
      </div>

      {lowStock.length > 0 ? (
        <p
          className="mt-4 rounded-lg px-4 py-3 text-sm"
          style={{ background: "var(--warning-soft)", color: "var(--warning)" }}
        >
          {lowStock.length} product{lowStock.length === 1 ? "" : "s"} at 5 or fewer in stock.
        </p>
      ) : null}

      <div className="mt-3">
        {loading ? (
          <SkeletonRows />
        ) : !products.length ? (
          <EmptyState
            title="No products yet"
            body="Add your first item, or import a CSV / Excel sheet using the template."
            action={
              <Button variant="primary" onClick={openCreate}>
                Add product
              </Button>
            }
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-left text-sm">
              <thead>
                <tr className="border-b text-[var(--text-secondary)]" style={{ borderColor: "var(--border)" }}>
                  <th className="py-2 font-medium">SKU</th>
                  <th className="py-2 font-medium">Name</th>
                  <th className="py-2 font-medium">Details</th>
                  <th className="py-2 font-medium text-right">Qty</th>
                  <th className="py-2 font-medium text-right">Price</th>
                  <th className="py-2 font-medium" />
                </tr>
              </thead>
              <tbody>
                {products.map((p) => (
                  <tr key={p.id} className="border-b" style={{ borderColor: "var(--border)" }}>
                    <td className="py-3 tabular">{p.sku || "—"}</td>
                    <td className="py-3 font-medium">{p.name}</td>
                    <td className="py-3 text-[var(--text-secondary)]">{p.serial_number || "—"}</td>
                    <td className={`py-3 text-right tabular ${p.qty <= 5 ? "text-[var(--warning)]" : ""}`}>
                      {p.qty}
                    </td>
                    <td className="py-3 text-right tabular">{formatCurrency(p.price)}</td>
                    <td className="py-3 text-right">
                      <button
                        type="button"
                        className="focus-ring mr-3 text-[var(--accent)]"
                        onClick={() => openEdit(p)}
                      >
                        Edit
                      </button>
                      <button
                        type="button"
                        className="focus-ring text-[var(--danger)]"
                        onClick={() => setDeleteId(p.id)}
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <Dialog
        open={editorOpen}
        title={draft.id ? "Edit product" : "Add product"}
        onClose={() => setEditorOpen(false)}
      >
        <div className="grid gap-3">
          <div className="grid grid-cols-3 gap-2">
            <Field label="SKU">
              <input
                className={inputClass}
                style={inputStyle()}
                value={draft.sku}
                onChange={(e) => setDraft({ ...draft, sku: e.target.value })}
              />
            </Field>
            <Field label="Price">
              <input
                className={`${inputClass} tabular`}
                style={inputStyle()}
                value={draft.price}
                onChange={(e) => setDraft({ ...draft, price: Number(e.target.value) || 0 })}
              />
            </Field>
            <Field label="Qty">
              <input
                className={`${inputClass} tabular`}
                style={inputStyle()}
                value={draft.qty}
                onChange={(e) => setDraft({ ...draft, qty: Number(e.target.value) || 0 })}
              />
            </Field>
          </div>
          <Field label="Name">
            <input
              className={inputClass}
              style={inputStyle()}
              value={draft.name}
              onChange={(e) => setDraft({ ...draft, name: e.target.value })}
            />
          </Field>
          <Field label="Details">
            <input
              className={inputClass}
              style={inputStyle()}
              value={draft.serial_number}
              onChange={(e) => setDraft({ ...draft, serial_number: e.target.value })}
              placeholder="Color, size, notes"
            />
          </Field>
          <div className="mt-2 flex flex-wrap gap-2">
            <Button variant="primary" onClick={() => save(false)}>
              Save next · F5
            </Button>
            <Button onClick={() => save(true)}>Save close · F6</Button>
            <Button variant="ghost" onClick={() => setEditorOpen(false)}>
              Cancel
            </Button>
          </div>
        </div>
      </Dialog>

      <Dialog
        open={deleteId !== null}
        title="Delete product"
        onClose={() => setDeleteId(null)}
      >
        <p className="text-sm text-[var(--text-secondary)]">
          This removes the product from inventory. Past invoices keep their line items.
        </p>
        <div className="mt-4 flex gap-2">
          <Button
            variant="danger"
            onClick={() => {
              if (deleteId == null) return;
              deleteProduct(getDatabase(), deleteId);
              schedulePersist();
              setDeleteId(null);
              refresh();
              toast.push("Product deleted", "success");
            }}
          >
            Delete
          </Button>
          <Button variant="ghost" onClick={() => setDeleteId(null)}>
            Cancel
          </Button>
        </div>
      </Dialog>
    </div>
  );
}
