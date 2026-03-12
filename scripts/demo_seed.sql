-- Minimal demo schema compatible with default mapping.

CREATE TABLE IF NOT EXISTS leads (
  id TEXT PRIMARY KEY,
  created_at TIMESTAMP,
  updated_at TIMESTAMP,
  stage TEXT,
  status TEXT,
  lost_reason TEXT,
  target_action_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS messages (
  id TEXT PRIMARY KEY,
  lead_id TEXT,
  created_at TIMESTAMP,
  direction TEXT,
  role TEXT,
  text TEXT,
  intent TEXT,
  confidence REAL,
  service_topic TEXT
);

CREATE TABLE IF NOT EXISTS ai_runs (
  id TEXT PRIMARY KEY,
  lead_id TEXT,
  created_at TIMESTAMP,
  intent TEXT,
  confidence REAL,
  handoff_to_human BOOLEAN,
  status TEXT,
  latency_ms REAL,
  prompt_tokens INTEGER,
  completion_tokens INTEGER
);

CREATE TABLE IF NOT EXISTS bookings (
  id TEXT PRIMARY KEY,
  lead_id TEXT,
  created_at TIMESTAMP,
  service_name TEXT,
  status TEXT
);

CREATE TABLE IF NOT EXISTS stage_events (
  id TEXT PRIMARY KEY,
  lead_id TEXT,
  changed_at TIMESTAMP,
  from_stage TEXT,
  to_stage TEXT
);

CREATE TABLE IF NOT EXISTS follow_ups (
  id TEXT PRIMARY KEY,
  lead_id TEXT,
  sent_at TIMESTAMP,
  response_at TIMESTAMP
);

INSERT INTO leads (id, created_at, updated_at, stage, status) VALUES
('l1', '2026-03-10T08:30:00+00:00', '2026-03-10T10:00:00+00:00', 'qualified', 'active'),
('l2', '2026-03-10T09:00:00+00:00', '2026-03-10T12:00:00+00:00', 'lost', 'lost');

INSERT INTO messages (id, lead_id, created_at, direction, role, text, intent, confidence, service_topic) VALUES
('m1', 'l1', '2026-03-10T08:31:00+00:00', 'in', 'user', 'Сколько стоит консультация?', 'price_question', 0.9, 'consulting'),
('m2', 'l1', '2026-03-10T08:32:00+00:00', 'out', 'assistant', 'Стоимость зависит от формата.', 'price_question', 0.95, 'consulting'),
('m3', 'l2', '2026-03-10T11:00:00+00:00', 'in', 'user', 'Мне дорого', 'objection', 0.88, 'consulting');

INSERT INTO stage_events (id, lead_id, changed_at, from_stage, to_stage) VALUES
('s1', 'l2', '2026-03-10T12:00:00+00:00', 'objection', 'lost');
