import initSqlJs, { type Database, type SqlJsStatic } from "sql.js";
import sqlWasmUrl from "sql.js/dist/sql-wasm.wasm?url";
import { initSchema, type SqlJsDatabase } from "./queries";

const IDB_NAME = "retail-invoice";
const IDB_STORE = "files";
const DB_KEY = "invoices.db";

let SQL: SqlJsStatic | null = null;
let db: Database | null = null;
let persistTimer: ReturnType<typeof setTimeout> | null = null;

async function isTauri(): Promise<boolean> {
  try {
    const { isTauri: check } = await import("@tauri-apps/api/core");
    return check();
  } catch {
    return false;
  }
}

async function getTauriDbPath(): Promise<string> {
  const { appDataDir, join } = await import("@tauri-apps/api/path");
  const base = await appDataDir();
  return join(base, "retail-invoice", "invoices.db");
}

function openIdb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(IDB_NAME, 1);
    req.onupgradeneeded = () => {
      const store = req.result.createObjectStore(IDB_STORE);
      void store;
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

async function loadBytesFromIdb(): Promise<Uint8Array | null> {
  const idb = await openIdb();
  return new Promise((resolve, reject) => {
    const tx = idb.transaction(IDB_STORE, "readonly");
    const req = tx.objectStore(IDB_STORE).get(DB_KEY);
    req.onsuccess = () => {
      const val = req.result;
      if (val instanceof Uint8Array) resolve(val);
      else if (val instanceof ArrayBuffer) resolve(new Uint8Array(val));
      else resolve(null);
    };
    req.onerror = () => reject(req.error);
  });
}

async function saveBytesToIdb(bytes: Uint8Array): Promise<void> {
  const idb = await openIdb();
  return new Promise((resolve, reject) => {
    const tx = idb.transaction(IDB_STORE, "readwrite");
    tx.objectStore(IDB_STORE).put(bytes, DB_KEY);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

async function loadBytesFromTauri(): Promise<Uint8Array | null> {
  const { exists, mkdir, readFile } = await import("@tauri-apps/plugin-fs");
  const { dirname } = await import("@tauri-apps/api/path");
  const path = await getTauriDbPath();
  const dir = await dirname(path);
  if (!(await exists(dir))) {
    await mkdir(dir, { recursive: true });
  }
  if (!(await exists(path))) return null;
  const data = await readFile(path);
  return data;
}

async function saveBytesToTauri(bytes: Uint8Array): Promise<void> {
  const { exists, mkdir, writeFile } = await import("@tauri-apps/plugin-fs");
  const { dirname } = await import("@tauri-apps/api/path");
  const path = await getTauriDbPath();
  const dir = await dirname(path);
  if (!(await exists(dir))) {
    await mkdir(dir, { recursive: true });
  }
  await writeFile(path, bytes);
}

function isWasmMagic(buffer: ArrayBuffer): boolean {
  if (buffer.byteLength < 4) return false;
  const header = new Uint8Array(buffer, 0, 4);
  // \0asm
  return header[0] === 0x00 && header[1] === 0x61 && header[2] === 0x73 && header[3] === 0x6d;
}

async function loadSqlWasm(): Promise<SqlJsStatic> {
  if (SQL) return SQL;

  const response = await fetch(sqlWasmUrl);
  if (!response.ok) {
    throw new Error(`Could not load the local database engine (${response.status})`);
  }
  const wasmBinary = await response.arrayBuffer();
  if (!isWasmMagic(wasmBinary)) {
    throw new Error(
      "Could not load the local database engine. Reinstall the app, or run npm run tauri:dev from source.",
    );
  }

  SQL = await initSqlJs({ wasmBinary });
  return SQL;
}

export async function openDatabase(): Promise<SqlJsDatabase> {
  if (db) return db as unknown as SqlJsDatabase;
  const sql = await loadSqlWasm();
  const tauri = await isTauri();
  let bytes: Uint8Array | null = null;
  try {
    bytes = tauri ? await loadBytesFromTauri() : await loadBytesFromIdb();
  } catch {
    bytes = null;
  }
  db = bytes ? new sql.Database(bytes) : new sql.Database();
  initSchema(db as unknown as SqlJsDatabase);
  await persistDatabase();
  return db as unknown as SqlJsDatabase;
}

export function getDatabase(): SqlJsDatabase {
  if (!db) throw new Error("Database not open");
  return db as unknown as SqlJsDatabase;
}

export async function persistDatabase(): Promise<void> {
  if (!db) return;
  const bytes = db.export();
  const tauri = await isTauri();
  if (tauri) {
    await saveBytesToTauri(bytes);
  } else {
    await saveBytesToIdb(bytes);
  }
}

export function schedulePersist(): void {
  if (persistTimer) clearTimeout(persistTimer);
  persistTimer = setTimeout(() => {
    void persistDatabase();
  }, 200);
}

export async function exportDatabaseBytes(): Promise<Uint8Array> {
  const database = await openDatabase();
  return (database as unknown as Database).export();
}

export async function replaceDatabaseFromBytes(bytes: Uint8Array): Promise<SqlJsDatabase> {
  const sql = await loadSqlWasm();
  if (db) {
    db.close();
    db = null;
  }
  db = new sql.Database(bytes);
  initSchema(db as unknown as SqlJsDatabase);
  await persistDatabase();
  return db as unknown as SqlJsDatabase;
}

export async function openDatabaseFromBytes(bytes: Uint8Array): Promise<SqlJsDatabase> {
  const sql = await loadSqlWasm();
  return new sql.Database(bytes) as unknown as SqlJsDatabase;
}

export async function getDbFilePathLabel(): Promise<string> {
  if (await isTauri()) {
    try {
      return await getTauriDbPath();
    } catch {
      return "Local app data (invoices.db)";
    }
  }
  return "This browser (IndexedDB — local only)";
}
