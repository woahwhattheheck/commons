CREATE TABLE IF NOT EXISTS posts (
  id TEXT PRIMARY KEY,
  content_sha256 TEXT NOT NULL,
  core_json TEXT NOT NULL,
  canonical_state TEXT NOT NULL,
  first_seen TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS conflicts (
  id TEXT NOT NULL,
  content_sha256 TEXT NOT NULL,
  from_node TEXT,
  at TEXT,
  PRIMARY KEY (id, content_sha256)
);
CREATE TABLE IF NOT EXISTS receipts (
  seq INTEGER PRIMARY KEY AUTOINCREMENT,
  id TEXT NOT NULL,
  service TEXT,
  state TEXT,
  at TEXT,
  extra TEXT
);
CREATE TABLE IF NOT EXISTS outbox (
  id TEXT PRIMARY KEY,
  content_sha256 TEXT NOT NULL,
  core_json TEXT NOT NULL,
  queued_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS cursors (
  peer TEXT PRIMARY KEY,
  through_cursor INTEGER,
  at TEXT
);
CREATE TABLE IF NOT EXISTS manifest (
  k TEXT PRIMARY KEY,
  v TEXT NOT NULL
);
