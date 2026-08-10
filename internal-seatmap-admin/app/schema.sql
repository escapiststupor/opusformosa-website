CREATE TABLE IF NOT EXISTS events (
  event_id TEXT PRIMARY KEY,
  program_id TEXT,
  slug TEXT,
  parent_seating_chart_id INTEGER,
  date_label TEXT,
  title TEXT,
  venue TEXT,
  sort_order INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS seats (
  event_id TEXT NOT NULL,
  floor_id TEXT NOT NULL,
  row_id TEXT NOT NULL,
  seat_number TEXT NOT NULL,
  svg_id TEXT,
  section_id TEXT,
  section_name TEXT,
  price INTEGER,
  kind TEXT,
  color TEXT,
  opentix_status TEXT,
  taken INTEGER NOT NULL DEFAULT 0,
  taken_source TEXT,
  r_x REAL,
  r_y REAL,
  raw_json TEXT,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (event_id, floor_id, row_id, seat_number),
  FOREIGN KEY (event_id) REFERENCES events(event_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS seat_overrides (
  event_id TEXT NOT NULL,
  floor_id TEXT NOT NULL,
  row_id TEXT NOT NULL,
  seat_number TEXT NOT NULL,
  admin_status TEXT NOT NULL CHECK (
    admin_status IN (
      'vip_available',
      'vip_assigned',
      'taken',
      'pulled',
      'public_sold',
      'closed'
    )
  ),
  assignee_name TEXT,
  note TEXT,
  source TEXT,
  source_record_id TEXT,
  updated_by TEXT,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (event_id, floor_id, row_id, seat_number),
  FOREIGN KEY (event_id, floor_id, row_id, seat_number)
    REFERENCES seats(event_id, floor_id, row_id, seat_number)
    ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS audit_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_id TEXT NOT NULL,
  floor_id TEXT NOT NULL,
  row_id TEXT NOT NULL,
  seat_number TEXT NOT NULL,
  action TEXT NOT NULL,
  old_value TEXT,
  new_value TEXT,
  actor_email TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_seats_event ON seats(event_id);
CREATE INDEX IF NOT EXISTS idx_seats_lookup ON seats(event_id, floor_id, row_id, seat_number);
CREATE INDEX IF NOT EXISTS idx_overrides_status ON seat_overrides(event_id, admin_status);
CREATE INDEX IF NOT EXISTS idx_overrides_assignee ON seat_overrides(event_id, assignee_name);
