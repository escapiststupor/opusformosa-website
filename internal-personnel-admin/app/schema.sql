CREATE TABLE IF NOT EXISTS people (
  id TEXT PRIMARY KEY,
  display_name TEXT NOT NULL,
  legal_name_zh TEXT,
  legal_name_en TEXT,
  email TEXT,
  phone TEXT,
  line_id TEXT,
  nationality TEXT,
  residency_status TEXT,
  birth_date TEXT,
  professional_experience TEXT,
  id_document_type TEXT,
  id_document_number TEXT,
  id_document_status TEXT NOT NULL DEFAULT 'missing'
    CHECK (id_document_status IN ('missing', 'received', 'verified')),
  id_document_note TEXT,
  permanent_address TEXT,
  mailing_address TEXT,
  bank_name TEXT,
  bank_code TEXT,
  bank_branch TEXT,
  bank_branch_code TEXT,
  bank_account_holder TEXT,
  bank_account_number TEXT,
  notes TEXT,
  is_active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS person_roles (
  person_id TEXT NOT NULL,
  role_name TEXT NOT NULL,
  PRIMARY KEY (person_id, role_name),
  FOREIGN KEY (person_id) REFERENCES people(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS audit_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  person_id TEXT NOT NULL,
  action TEXT NOT NULL,
  actor_email TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (person_id) REFERENCES people(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_people_name ON people(display_name);
CREATE INDEX IF NOT EXISTS idx_people_active ON people(is_active);
CREATE INDEX IF NOT EXISTS idx_person_roles_name ON person_roles(role_name);

CREATE TABLE IF NOT EXISTS person_documents (
  id TEXT PRIMARY KEY,
  person_id TEXT NOT NULL,
  original_filename TEXT NOT NULL,
  stored_filename TEXT NOT NULL UNIQUE,
  storage_path TEXT,
  content_type TEXT,
  file_size TEXT NOT NULL,
  uploaded_by TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (person_id) REFERENCES people(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_person_documents_person ON person_documents(person_id, created_at DESC);

CREATE TABLE IF NOT EXISTS labor_reports (
  id TEXT PRIMARY KEY,
  person_id TEXT NOT NULL,
  recipient_name TEXT NOT NULL,
  id_document_type TEXT NOT NULL,
  id_document_number TEXT NOT NULL,
  work_date TEXT NOT NULL,
  work_start_date TEXT,
  work_end_date TEXT,
  work_description TEXT NOT NULL,
  issue_date TEXT NOT NULL,
  payment_month TEXT NOT NULL,
  income_category TEXT NOT NULL,
  payment_method TEXT NOT NULL CHECK (payment_method IN ('wire', 'cash')),
  gross_amount INTEGER NOT NULL CHECK (gross_amount >= 0),
  withholding_rate REAL NOT NULL DEFAULT 0,
  withholding_tax INTEGER NOT NULL DEFAULT 0,
  supplemental_health_insurance INTEGER NOT NULL DEFAULT 0,
  net_amount INTEGER NOT NULL,
  bank_name TEXT,
  bank_code TEXT,
  bank_branch TEXT,
  bank_branch_code TEXT,
  bank_account_holder TEXT,
  bank_account_number TEXT,
  unsigned_storage_path TEXT NOT NULL,
  signed_storage_path TEXT,
  signed_original_filename TEXT,
  signed_uploaded_by TEXT,
  signed_at TEXT,
  voided_at TEXT,
  voided_by TEXT,
  created_by TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (person_id) REFERENCES people(id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_labor_reports_person ON labor_reports(person_id, work_date DESC);
CREATE INDEX IF NOT EXISTS idx_labor_reports_payment_month ON labor_reports(payment_month, income_category);

CREATE TABLE IF NOT EXISTS reimbursements (
  id TEXT PRIMARY KEY,
  person_id TEXT NOT NULL,
  payment_month TEXT NOT NULL,
  amount INTEGER NOT NULL CHECK (amount >= 0),
  notes TEXT,
  created_by TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (person_id) REFERENCES people(id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_reimbursements_payment_month ON reimbursements(payment_month, person_id);

CREATE TABLE IF NOT EXISTS labor_report_emails (
  id TEXT PRIMARY KEY,
  labor_report_id TEXT NOT NULL,
  recipient_email TEXT NOT NULL,
  subject TEXT NOT NULL,
  body TEXT NOT NULL,
  sent_by TEXT NOT NULL,
  sent_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (labor_report_id) REFERENCES labor_reports(id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_labor_report_emails_report ON labor_report_emails(labor_report_id, sent_at DESC);
