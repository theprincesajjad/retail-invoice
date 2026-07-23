export type PlatformKind = "mac" | "windows" | "other";

export function detectPlatform(): PlatformKind {
  const ua = navigator.platform || navigator.userAgent;
  if (/Mac|iPhone|iPad|iPod/i.test(ua)) return "mac";
  if (/Win/i.test(ua)) return "windows";
  return "other";
}

export function isMac(): boolean {
  return detectPlatform() === "mac";
}

export interface ShortcutRow {
  action: string;
  windows: string;
  mac: string;
}

export const SHORTCUTS: ShortcutRow[] = [
  { action: "Sale tab", windows: "F1", mac: "⌘ 1" },
  { action: "Products tab", windows: "F2", mac: "⌘ 2" },
  { action: "History tab", windows: "F3", mac: "⌘ 3" },
  { action: "Setup tab", windows: "F4", mac: "⌘ 4" },
  { action: "Save sale as PDF", windows: "F10", mac: "⌘ S" },
  { action: "Preview receipt", windows: "F11", mac: "⌘ P" },
  { action: "Complete sale", windows: "F12", mac: "⌘ ⏎" },
  { action: "Pay with cash (in prompt)", windows: "F7", mac: "⌘ 7" },
  { action: "Pay with card (in prompt)", windows: "F8", mac: "⌘ 8" },
];

export function shortcutLabel(windows: string, mac: string): string {
  return isMac() ? mac : windows;
}

export function tabShortcut(tabIndex: 1 | 2 | 3 | 4): string {
  return isMac() ? `⌘ ${tabIndex}` : `F${tabIndex}`;
}
