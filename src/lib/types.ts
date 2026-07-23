export type DiscountType = "" | "percent" | "fixed";
export type DiscountTiming = "before_tax" | "after_tax";
export type PaymentMethod = "Cash" | "Card" | "Other";
export type ThemePreference = "light" | "dark" | "system";
export type AppTab = "sale" | "products" | "history" | "setup";

export interface Product {
  id: number | null;
  name: string;
  serial_number: string;
  sku: string;
  price: number;
  qty: number;
  category: string;
  created_at?: string;
}

export interface InvoiceItem {
  id?: number | null;
  invoice_id?: number | null;
  product_id: number | null;
  description: string;
  serial_number: string;
  qty: number;
  unit_price: number;
  line_total: number;
}

export interface Invoice {
  id: number | null;
  invoice_number: string;
  customer_name: string;
  customer_phone: string;
  customer_email: string;
  subtotal: number;
  tax_rate: number;
  tax_amount: number;
  total: number;
  payment_method: PaymentMethod | string;
  notes: string;
  created_at: string;
  items: InvoiceItem[];
  discount_type: DiscountType | string;
  discount_value: number;
  discount_amount: number;
  discount_timing: DiscountTiming | string;
}

export interface AppSettings {
  business_name: string;
  business_tagline: string;
  business_address: string;
  business_website: string;
  business_phone: string;
  business_email: string;
  gst_number: string;
  receipt_footer: string;
  tax_rate: string;
  discount_timing: DiscountTiming | string;
  logo_path: string;
  receipt_width: string;
  receipt_font_size: string;
  receipt_header_spacing: string;
  receipt_show_logo: string;
  receipt_show_business_name: string;
  receipt_show_tagline: string;
  receipt_show_address: string;
  receipt_show_phone: string;
  receipt_show_website: string;
  receipt_show_email: string;
  receipt_show_customer: string;
  receipt_show_details: string;
  receipt_show_notes: string;
  receipt_show_thanks: string;
  receipt_show_footer: string;
  receipt_show_gst: string;
  smtp_host: string;
  smtp_port: string;
  smtp_email: string;
  smtp_password: string;
  smtp_from_name: string;
  setup_complete: string;
  theme_preference: ThemePreference | string;
  [key: string]: string;
}

export const DEFAULT_SETTINGS: AppSettings = {
  business_name: "My Business",
  business_tagline: "",
  business_address: "123 Main St, City, ON",
  business_website: "",
  business_phone: "(416) 555-0123",
  business_email: "",
  gst_number: "123456789RT0001",
  receipt_footer: "All Sales are Final. No Returns or Exchanges.",
  tax_rate: "0.13",
  discount_timing: "before_tax",
  logo_path: "",
  receipt_width: "80mm",
  receipt_font_size: "normal",
  receipt_header_spacing: "normal",
  receipt_show_logo: "1",
  receipt_show_business_name: "1",
  receipt_show_tagline: "1",
  receipt_show_address: "1",
  receipt_show_phone: "1",
  receipt_show_website: "1",
  receipt_show_email: "1",
  receipt_show_customer: "1",
  receipt_show_details: "1",
  receipt_show_notes: "1",
  receipt_show_thanks: "1",
  receipt_show_footer: "1",
  receipt_show_gst: "1",
  smtp_host: "smtp.gmail.com",
  smtp_port: "587",
  smtp_email: "",
  smtp_password: "",
  smtp_from_name: "My Business",
  setup_complete: "",
  theme_preference: "light",
};

export interface InvoiceTotals {
  subtotal: number;
  discount_amount: number;
  tax_amount: number;
  total: number;
}
