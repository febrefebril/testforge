-- TestForge Healing Knowledge Base - schema inicial

CREATE TABLE IF NOT EXISTS technology_profile_detection (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at INTEGER NOT NULL,
    application TEXT NOT NULL,
    page_signature TEXT NOT NULL,
    detected_family TEXT NOT NULL,
    confidence REAL NOT NULL,
    hints_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS healing_suggestion (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at INTEGER NOT NULL,
    run_id TEXT NOT NULL,
    application TEXT NOT NULL,
    page_signature TEXT NOT NULL,
    action_id TEXT NOT NULL,
    technology_family TEXT,
    taxonomy_code TEXT NOT NULL,
    original_locator TEXT NOT NULL,
    suggested_locator TEXT NOT NULL,
    total_score REAL NOT NULL,
    semantic_score REAL,
    uniqueness_score REAL,
    actionability_score REAL,
    oracle_score REAL,
    historical_score REAL,
    mode TEXT NOT NULL, -- shadow | canary | auto
    status TEXT NOT NULL -- suggested | reviewed | promoted | rejected | deprecated
);

CREATE TABLE IF NOT EXISTS oracle_observation (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at INTEGER NOT NULL,
    healing_suggestion_id INTEGER NOT NULL,
    oracle_type TEXT NOT NULL,
    expected TEXT NOT NULL,
    actual TEXT,
    result TEXT NOT NULL, -- passed | failed | inconclusive
    reviewed_label TEXT, -- TP | FP | TN | FN
    evidence_ref TEXT,
    FOREIGN KEY (healing_suggestion_id) REFERENCES healing_suggestion(id)
);

CREATE TABLE IF NOT EXISTS evidence_package (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at INTEGER NOT NULL,
    healing_suggestion_id INTEGER NOT NULL,
    screenshot_before TEXT,
    screenshot_after TEXT,
    dom_before TEXT,
    dom_after TEXT,
    ax_tree_before TEXT,
    ax_tree_after TEXT,
    network_log TEXT,
    trace_ref TEXT,
    score_breakdown_json TEXT,
    FOREIGN KEY (healing_suggestion_id) REFERENCES healing_suggestion(id)
);

CREATE TABLE IF NOT EXISTS review_decision (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at INTEGER NOT NULL,
    healing_suggestion_id INTEGER NOT NULL,
    reviewer TEXT,
    label TEXT NOT NULL, -- TRUE_POSITIVE_HEAL | FALSE_HEAL | NOT_RECOVERABLE | ORACLE_WEAK | TAXONOMY_WRONG | TECHNOLOGY_PROFILE_WRONG | INCONCLUSIVE
    notes TEXT,
    promote_to_state TEXT,
    FOREIGN KEY (healing_suggestion_id) REFERENCES healing_suggestion(id)
);

CREATE TABLE IF NOT EXISTS synthetic_mutation_result (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at INTEGER NOT NULL,
    fake_app TEXT NOT NULL,
    technology_family TEXT NOT NULL,
    mutation_family TEXT NOT NULL,
    mutation_code TEXT NOT NULL,
    expected_taxonomy_code TEXT NOT NULL,
    observed_taxonomy_code TEXT,
    expected_recoverable INTEGER NOT NULL,
    observed_recovered INTEGER,
    false_heal INTEGER DEFAULT 0,
    evidence_ref TEXT
);
