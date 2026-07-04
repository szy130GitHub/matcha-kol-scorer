-- Matcha KOL Scorer — SQLite Schema v0.1 (2026-07-04)
-- Timestamps are ISO8601 UTC strings. Platform ∈ {'douyin', 'xhs'}.

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS id_resolution (
  platform       TEXT NOT NULL,
  handle         TEXT NOT NULL,
  display_name   TEXT,
  resolved_id    TEXT,
  xsec_token     TEXT,
  xsec_source    TEXT,
  profile_url    TEXT,
  status         TEXT NOT NULL,
  resolved_at    TEXT NOT NULL,
  expires_at     TEXT,
  raw_candidates TEXT,
  PRIMARY KEY (platform, handle)
);
CREATE INDEX IF NOT EXISTS idx_resolution_status ON id_resolution(status);
CREATE INDEX IF NOT EXISTS idx_resolution_platform ON id_resolution(platform);

CREATE TABLE IF NOT EXISTS creator (
  platform         TEXT NOT NULL,
  resolved_id      TEXT NOT NULL,
  handle           TEXT NOT NULL,
  nickname         TEXT,
  signature        TEXT,
  avatar_url       TEXT,
  follower_count   INTEGER,
  following_count  INTEGER,
  total_liked      INTEGER,
  total_collected  INTEGER,
  notes_count      INTEGER,
  gender           TEXT,
  location         TEXT,
  level            TEXT,
  verified         INTEGER DEFAULT 0,
  fetched_at       TEXT NOT NULL,
  raw_json         TEXT,
  PRIMARY KEY (platform, resolved_id)
);
CREATE INDEX IF NOT EXISTS idx_creator_handle ON creator(platform, handle);
CREATE INDEX IF NOT EXISTS idx_creator_follower ON creator(follower_count DESC);

CREATE TABLE IF NOT EXISTS note (
  platform         TEXT NOT NULL,
  resolved_id      TEXT NOT NULL,
  note_id          TEXT NOT NULL,
  title            TEXT,
  description      TEXT,
  note_type        TEXT,
  create_time      TEXT,
  liked_count      INTEGER,
  comment_count    INTEGER,
  collected_count  INTEGER,
  share_count      INTEGER,
  play_count       INTEGER,
  cover_url        TEXT,
  note_url         TEXT,
  tag_list         TEXT,
  xsec_token       TEXT,
  fetched_at       TEXT NOT NULL,
  raw_json         TEXT,
  PRIMARY KEY (platform, note_id)
);
CREATE INDEX IF NOT EXISTS idx_note_creator ON note(platform, resolved_id, create_time DESC);
CREATE INDEX IF NOT EXISTS idx_note_liked ON note(liked_count DESC);

CREATE TABLE IF NOT EXISTS score (
  id                    INTEGER PRIMARY KEY AUTOINCREMENT,
  task_id               TEXT NOT NULL,
  platform              TEXT NOT NULL,
  resolved_id           TEXT NOT NULL,
  handle                TEXT NOT NULL,
  nickname              TEXT,
  influence_score       REAL,
  engagement_score      REAL,
  stability_score       REAL,
  relevance_score       REAL,
  total_score           REAL NOT NULL,
  grade                 TEXT NOT NULL,
  follower_count        INTEGER,
  avg_liked             REAL,
  avg_comment           REAL,
  avg_collected         REAL,
  avg_share             REAL,
  engagement_rate       REAL,
  stability_ratio       REAL,
  relevance_hit_ratio   REAL,
  notes_analyzed        INTEGER,
  scored_at             TEXT NOT NULL,
  thresholds_version    TEXT,
  notes_json            TEXT,
  UNIQUE (task_id, platform, resolved_id)
);
CREATE INDEX IF NOT EXISTS idx_score_task ON score(task_id, total_score DESC);
CREATE INDEX IF NOT EXISTS idx_score_grade ON score(task_id, grade);

CREATE TABLE IF NOT EXISTS scan_task (
  task_id        TEXT PRIMARY KEY,
  name           TEXT,
  input_file     TEXT,
  target_count   INTEGER NOT NULL,
  status         TEXT NOT NULL,
  started_at     TEXT,
  finished_at    TEXT,
  stats_json     TEXT
);
CREATE INDEX IF NOT EXISTS idx_task_status ON scan_task(status);

CREATE TABLE IF NOT EXISTS scan_progress (
  task_id        TEXT NOT NULL,
  platform       TEXT NOT NULL,
  resolved_id    TEXT NOT NULL,
  handle         TEXT NOT NULL,
  status         TEXT NOT NULL,
  retry_count    INTEGER DEFAULT 0,
  last_error     TEXT,
  updated_at     TEXT NOT NULL,
  PRIMARY KEY (task_id, platform, resolved_id)
);
CREATE INDEX IF NOT EXISTS idx_progress_status ON scan_progress(task_id, status);

CREATE TABLE IF NOT EXISTS rate_limit_event (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  platform        TEXT NOT NULL,
  code            TEXT NOT NULL,
  triggered_at    TEXT NOT NULL,
  cooldown_until  TEXT NOT NULL,
  context_json    TEXT
);
CREATE INDEX IF NOT EXISTS idx_ratelimit_platform_time ON rate_limit_event(platform, triggered_at DESC);

CREATE TABLE IF NOT EXISTS unresolved_log (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  task_id           TEXT,
  platform          TEXT NOT NULL,
  handle            TEXT NOT NULL,
  display_name      TEXT,
  reason            TEXT NOT NULL,
  candidates_json   TEXT,
  created_at        TEXT NOT NULL,
  resolved_manually INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_unresolved_task ON unresolved_log(task_id, resolved_manually);
