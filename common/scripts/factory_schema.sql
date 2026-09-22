-- ============================================================================
-- The Factory: the workshop's running example schema.
-- A multi-plant smart-manufacturing operation. Every journey runs against these
-- tables on YOUR branch. Loaded by common/scripts/load_factory.py during setup.
--
-- Design: clean, teachable names with real manufacturing structure
--   (multi-plant, MES work orders + operations, a bill-of-materials TREE,
--    supply chain, sensor telemetry, maintenance logs).
-- Standard Postgres only here; journeys add extensions (pgvector, PostGIS, ...)
-- on top when they need them.
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS factory;
SET search_path TO factory, public;

-- ---- Plants & assets (multi-plant; the digital-twin core) -------------------
CREATE TABLE IF NOT EXISTS plant (
    plant_id    TEXT PRIMARY KEY,          -- e.g. 'PL-DETROIT'
    name        TEXT NOT NULL,
    region      TEXT NOT NULL,             -- e.g. 'US-Midwest'
    operator    TEXT NOT NULL,             -- the business unit that runs it (RLS boundary later)
    lat         DOUBLE PRECISION,          -- becomes a PostGIS point in pg-geo
    lon         DOUBLE PRECISION
);

CREATE TABLE IF NOT EXISTS machine (
    machine_id  TEXT PRIMARY KEY,          -- e.g. 'M-204'
    plant_id    TEXT NOT NULL REFERENCES plant(plant_id),
    line        TEXT NOT NULL,             -- production line, e.g. 'Stamping-A'
    type        TEXT NOT NULL,             -- e.g. 'press', 'cnc', 'robot', 'conveyor'
    status      TEXT NOT NULL DEFAULT 'healthy',   -- healthy | derated | down | maintenance
    health_pct  NUMERIC(5,2) NOT NULL DEFAULT 100.0
);

-- Live telemetry off each machine. Time-series: partitioned in pg-partition,
-- streamed to the lakehouse in write-to-analytics.
CREATE TABLE IF NOT EXISTS sensor_reading (
    reading_id      BIGSERIAL PRIMARY KEY,
    machine_id      TEXT NOT NULL REFERENCES machine(machine_id),
    ts              TIMESTAMPTZ NOT NULL DEFAULT now(),
    temp_c          NUMERIC(6,2),
    vibration_mm_s  NUMERIC(6,2),
    rpm             INT,
    load_pct        NUMERIC(5,2)
);

-- ---- Bill of Materials (a TREE: product -> parts -> sub-parts) --------------
CREATE TABLE IF NOT EXISTS product (
    product_id  TEXT PRIMARY KEY,          -- e.g. 'PRD-GEARBOX-X1'
    name        TEXT NOT NULL,
    spec        JSONB DEFAULT '{}'::jsonb  -- flexible spec sheet (pg-json)
);

CREATE TABLE IF NOT EXISTS part (
    part_id     TEXT PRIMARY KEY,          -- e.g. 'PT-BEARING-6204'
    name        TEXT NOT NULL,
    part_type   TEXT NOT NULL,             -- e.g. 'bearing', 'gear', 'housing', 'fastener'
    spec        JSONB DEFAULT '{}'::jsonb  -- varying fields (pg-json); embedding added in pg-vector
);

-- The BOM edges: parent is a product OR a part; child is a part. qty per parent.
-- Recursive-CTE explosion in pg-sql-parity; graph in the kg-* journeys.
CREATE TABLE IF NOT EXISTS bom_edge (
    parent_id   TEXT NOT NULL,             -- product_id or part_id
    child_part  TEXT NOT NULL REFERENCES part(part_id),
    qty         INT NOT NULL DEFAULT 1,
    PRIMARY KEY (parent_id, child_part)
);

-- ---- MES (Manufacturing Execution System = the OLTP heart) -----------------
CREATE TABLE IF NOT EXISTS work_order (
    wo_id       TEXT PRIMARY KEY,          -- e.g. 'WO-8821'
    plant_id    TEXT NOT NULL REFERENCES plant(plant_id),
    product_id  TEXT NOT NULL REFERENCES product(product_id),
    qty         INT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'released',  -- released | in_progress | done | held
    due_ts      TIMESTAMPTZ
);

-- Routing steps of a work order, scheduled onto machines into time windows.
-- The `during` range powers the no-double-booking journey (GiST exclusion).
CREATE TABLE IF NOT EXISTS operation (
    op_id       TEXT PRIMARY KEY,          -- e.g. 'OP-1'
    wo_id       TEXT NOT NULL REFERENCES work_order(wo_id),
    machine_id  TEXT NOT NULL REFERENCES machine(machine_id),
    seq         INT NOT NULL,              -- step order within the work order
    status      TEXT NOT NULL DEFAULT 'pending',
    starts_at   TIMESTAMPTZ,
    ends_at     TIMESTAMPTZ
);

-- ---- Supply chain ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS supplier (
    supplier_id TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    lat         DOUBLE PRECISION,
    lon         DOUBLE PRECISION,
    spec        JSONB DEFAULT '{}'::jsonb  -- lead_time_weeks, quality_ppm, dual_source, ...
);

CREATE TABLE IF NOT EXISTS warehouse (
    warehouse_id TEXT PRIMARY KEY,
    plant_id     TEXT REFERENCES plant(plant_id),
    lat          DOUBLE PRECISION,
    lon          DOUBLE PRECISION,
    capacity     INT
);

CREATE TABLE IF NOT EXISTS inventory (
    part_id      TEXT NOT NULL REFERENCES part(part_id),
    warehouse_id TEXT NOT NULL REFERENCES warehouse(warehouse_id),
    qty          INT NOT NULL DEFAULT 0,
    PRIMARY KEY (part_id, warehouse_id)
);

-- Which supplier supplies which part (with per-supplier lead time on the edge).
CREATE TABLE IF NOT EXISTS part_supplier (
    part_id         TEXT NOT NULL REFERENCES part(part_id),
    supplier_id     TEXT NOT NULL REFERENCES supplier(supplier_id),
    lead_time_weeks INT,
    PRIMARY KEY (part_id, supplier_id)
);

-- ---- AI / ops: free-text maintenance write-ups -----------------------------
-- Read by the AI extraction / learning-loop / search journeys.
CREATE TABLE IF NOT EXISTS maintenance_log (
    log_id      BIGSERIAL PRIMARY KEY,
    machine_id  TEXT NOT NULL REFERENCES machine(machine_id),
    ts          TIMESTAMPTZ NOT NULL DEFAULT now(),
    writeup     TEXT NOT NULL,             -- the raw engineer note
    system      TEXT,                      -- AI-extracted: which subsystem
    defect      TEXT,                      -- AI-extracted: the defect
    action      TEXT,                      -- AI-extracted: action taken
    confidence  NUMERIC(4,3)               -- AI self-scored confidence (learning-loop)
);

-- Shared agent memory: the AI journeys' only link between agents.
CREATE TABLE IF NOT EXISTS agent_memory (
    id          BIGSERIAL PRIMARY KEY,
    namespace   TEXT NOT NULL DEFAULT 'default',
    session_id  TEXT NOT NULL DEFAULT 'sess-01',
    agent_id    TEXT NOT NULL,             -- e.g. 'maintenance_advisor', 'mes_assistant'
    role        TEXT NOT NULL,             -- user | assistant | system
    content     TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
