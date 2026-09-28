-- ============================================================================
-- The Bank: the finance edition's running example schema.
-- A retail + commercial bank's operational core. Every journey runs against
-- these tables on YOUR branch. Loaded by common/scripts/load_bank.py.
--
-- Design: clean, teachable names with real banking structure, mirroring the
-- STRUCTURE the journeys exercise (a tenancy boundary, a live "twin" with a
-- status/score, a high-volume time-series, a TREE for recursive queries + graph,
-- a booking/exclusion table, a counterparty network, free-text notes for AI).
-- Standard Postgres only here; journeys add extensions (pgvector, PostGIS, ...).
--
-- Table-role map (same roles as the manufacturing edition, real finance names):
--   branch        <- plant           (tenancy boundary + geo point)
--   account       <- machine         (the live operational "twin": status + risk)
--   txn           <- sensor_reading  (high-volume time-series)
--   fund          <- product         (root of the holdings tree)
--   instrument    <- part            (leaf of the holdings tree)
--   holding       <- bom_edge        (the tree edges: fund -> sub-fund -> instrument)
--   trade         <- work_order      (the OLTP order)
--   settlement    <- operation       (booked into a time window; GiST exclusion)
--   counterparty  <- supplier        (the supply-side network + geo)
--   custodian     <- warehouse
--   position      <- inventory
--   trade_counterparty <- part_supplier
--   case_note     <- maintenance_log (free text + AI-extracted fields)
--   agent_memory  <- agent_memory
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS bank;
SET search_path TO bank, public;

-- ---- Branches & accounts (tenancy boundary + the live "twin") ----------------
CREATE TABLE IF NOT EXISTS branch (
    branch_id   TEXT PRIMARY KEY,             -- e.g. 'BR-NYC'
    name        TEXT NOT NULL,
    region      TEXT NOT NULL,                -- e.g. 'US-Northeast'
    operator    TEXT NOT NULL,                -- business unit / legal entity (RLS boundary)
    lat         DOUBLE PRECISION,             -- becomes a PostGIS point in pg-geo
    lon         DOUBLE PRECISION
);

CREATE TABLE IF NOT EXISTS account (
    account_id  TEXT PRIMARY KEY,             -- e.g. 'ACCT-100234'
    branch_id   TEXT NOT NULL REFERENCES branch(branch_id),
    line        TEXT NOT NULL,                -- product line: 'Checking', 'Savings', 'Credit'
    type        TEXT NOT NULL,                -- 'retail', 'commercial', 'wealth'
    status      TEXT NOT NULL DEFAULT 'good_standing',  -- good_standing | watch | frozen | closed
    health_pct  NUMERIC(5,2) NOT NULL DEFAULT 100.0     -- account health (risk-inverse) score
);

-- High-volume transactions off each account. Time-series: partitioned in
-- pg-partition, streamed to the lakehouse in write-to-analytics (fraud scoring).
CREATE TABLE IF NOT EXISTS txn (
    txn_id          BIGSERIAL PRIMARY KEY,
    account_id      TEXT NOT NULL REFERENCES account(account_id),
    ts              TIMESTAMPTZ NOT NULL DEFAULT now(),
    amount_usd      NUMERIC(12,2),            -- transaction amount
    anomaly_score   NUMERIC(6,2),             -- 0-10, higher = riskier
    mcc             INT,                      -- merchant category code
    util_pct        NUMERIC(5,2)              -- account utilization at the time (%)
);

-- ---- Holdings tree (fund -> sub-fund -> instrument) --------------------------
CREATE TABLE IF NOT EXISTS fund (
    fund_id     TEXT PRIMARY KEY,             -- e.g. 'FUND-GROWTH-A'
    name        TEXT NOT NULL,
    spec        JSONB DEFAULT '{}'::jsonb     -- mandate/strategy sheet (pg-json)
);

CREATE TABLE IF NOT EXISTS instrument (
    instrument_id TEXT PRIMARY KEY,           -- e.g. 'INS-AAPL', 'INS-UST-10Y'
    name          TEXT NOT NULL,
    kind          TEXT NOT NULL,              -- 'equity', 'bond', 'etf', 'cash'
    spec          JSONB DEFAULT '{}'::jsonb   -- varying fields (pg-json); embedding in pg-vector
);

-- Holdings edges: parent is a fund OR a sub-fund; child is an instrument. qty = units.
-- Recursive-CTE holdings-explosion in pg-sql-parity; graph in the kg-* journeys.
CREATE TABLE IF NOT EXISTS holding (
    parent_id     TEXT NOT NULL,              -- fund_id or (sub-)instrument grouping id
    instrument_id TEXT NOT NULL REFERENCES instrument(instrument_id),
    qty           INT NOT NULL DEFAULT 1,     -- units held
    PRIMARY KEY (parent_id, instrument_id)
);

-- ---- Trades & settlement (OLTP heart + booking/exclusion) --------------------
CREATE TABLE IF NOT EXISTS trade (
    trade_id    TEXT PRIMARY KEY,             -- e.g. 'TRD-8821'
    branch_id   TEXT NOT NULL REFERENCES branch(branch_id),
    fund_id     TEXT NOT NULL REFERENCES fund(fund_id),
    qty         INT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'placed',  -- placed | executing | settled | cancelled
    due_ts      TIMESTAMPTZ                   -- settlement due
);

-- Settlement legs of a trade, booked onto an account into a time window.
-- A settlement slot on an account cannot overlap another (GiST exclusion).
CREATE TABLE IF NOT EXISTS settlement (
    settlement_id TEXT PRIMARY KEY,           -- e.g. 'STL-1'
    trade_id      TEXT NOT NULL REFERENCES trade(trade_id),
    account_id    TEXT NOT NULL REFERENCES account(account_id),
    seq           INT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'pending',
    starts_at     TIMESTAMPTZ,
    ends_at       TIMESTAMPTZ
);

-- ---- Counterparties & custody (the supply-side network) ----------------------
CREATE TABLE IF NOT EXISTS counterparty (
    counterparty_id TEXT PRIMARY KEY,         -- e.g. 'CP-GOLDMAN'
    name            TEXT NOT NULL,
    lat             DOUBLE PRECISION,
    lon             DOUBLE PRECISION,
    spec            JSONB DEFAULT '{}'::jsonb -- credit_rating, exposure_limit, dual_source, ...
);

CREATE TABLE IF NOT EXISTS custodian (
    custodian_id TEXT PRIMARY KEY,            -- e.g. 'CUST-BNY'
    branch_id    TEXT REFERENCES branch(branch_id),
    lat          DOUBLE PRECISION,
    lon          DOUBLE PRECISION,
    capacity     INT                          -- assets-under-custody capacity ($M)
);

CREATE TABLE IF NOT EXISTS position (
    instrument_id TEXT NOT NULL REFERENCES instrument(instrument_id),
    custodian_id  TEXT NOT NULL REFERENCES custodian(custodian_id),
    qty           INT NOT NULL DEFAULT 0,
    PRIMARY KEY (instrument_id, custodian_id)
);

-- Which counterparty trades which instrument (edge with a settlement lead time).
CREATE TABLE IF NOT EXISTS trade_counterparty (
    instrument_id   TEXT NOT NULL REFERENCES instrument(instrument_id),
    counterparty_id TEXT NOT NULL REFERENCES counterparty(counterparty_id),
    settle_days     INT,
    PRIMARY KEY (instrument_id, counterparty_id)
);

-- ---- AI / ops: free-text case notes (fraud / AML alerts) ---------------------
CREATE TABLE IF NOT EXISTS case_note (
    note_id     BIGSERIAL PRIMARY KEY,
    account_id  TEXT NOT NULL REFERENCES account(account_id),
    ts          TIMESTAMPTZ NOT NULL DEFAULT now(),
    writeup     TEXT NOT NULL,                -- raw analyst note on an alert
    category    TEXT,                         -- AI-extracted: fraud | AML | dispute | ...
    finding     TEXT,                         -- AI-extracted: the finding
    action      TEXT,                         -- AI-extracted: action taken
    confidence  NUMERIC(4,3)                  -- AI self-scored confidence (learning-loop)
);

-- Shared agent memory: the AI journeys' only link between agents.
CREATE TABLE IF NOT EXISTS agent_memory (
    id          BIGSERIAL PRIMARY KEY,
    namespace   TEXT NOT NULL DEFAULT 'default',
    session_id  TEXT NOT NULL DEFAULT 'sess-01',
    agent_id    TEXT NOT NULL,                -- e.g. 'fraud_advisor', 'ops_assistant'
    role        TEXT NOT NULL,
    content     TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
