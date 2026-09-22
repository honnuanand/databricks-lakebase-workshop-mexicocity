-- ============================================================================
-- Seed data for the Factory running example. Small, hand-built, and legible so
-- you can reason about query results. Journeys that need scale (50k+ rows, e.g.
-- pg-explain, pg-index, pg-partition) generate their own data on top of this.
-- Loaded by common/scripts/load_factory.py after factory_schema.sql.
-- ============================================================================
SET search_path TO factory, public;

-- ---- Plants (3 plants, 3 business units) -----------------------------------
INSERT INTO plant (plant_id, name, region, operator, lat, lon) VALUES
  ('PL-DETROIT', 'Detroit Stamping',   'US-Midwest',   'NorthAxle',  42.3314, -83.0458),
  ('PL-AUSTIN',  'Austin Assembly',    'US-South',     'NorthAxle',  30.2672, -97.7431),
  ('PL-MUNICH',  'Munich Precision',   'EU-Central',   'EuroDrive',  48.1351,  11.5820)
ON CONFLICT (plant_id) DO NOTHING;

-- ---- Machines (a few per plant, on named lines) ----------------------------
INSERT INTO machine (machine_id, plant_id, line, type, status, health_pct) VALUES
  ('M-101', 'PL-DETROIT', 'Stamping-A', 'press',    'healthy',     98.5),
  ('M-102', 'PL-DETROIT', 'Stamping-A', 'robot',    'healthy',     96.2),
  ('M-204', 'PL-DETROIT', 'Stamping-B', 'press',    'healthy',     91.0),
  ('M-205', 'PL-DETROIT', 'Stamping-B', 'conveyor', 'healthy',     99.1),
  ('M-310', 'PL-AUSTIN',  'Assembly-1', 'robot',    'healthy',     94.7),
  ('M-311', 'PL-AUSTIN',  'Assembly-1', 'cnc',      'maintenance', 88.0),
  ('M-420', 'PL-MUNICH',  'Precision-1','cnc',      'healthy',     97.3),
  ('M-421', 'PL-MUNICH',  'Precision-1','robot',    'derated',     82.4)
ON CONFLICT (machine_id) DO NOTHING;

-- ---- A few sensor readings per machine (journeys generate more as needed) --
INSERT INTO sensor_reading (machine_id, ts, temp_c, vibration_mm_s, rpm, load_pct) VALUES
  ('M-204', now() - interval '10 min', 62.5, 2.1, 1180, 74.0),
  ('M-204', now() - interval  '5 min', 63.1, 2.4, 1180, 76.5),
  ('M-204', now() - interval  '1 min', 64.0, 3.8, 1175, 78.2),   -- vibration creeping up
  ('M-421', now() - interval  '5 min', 71.2, 5.6,  980, 91.0),   -- derated machine runs hot
  ('M-101', now() - interval  '5 min', 55.0, 1.2, 1200, 60.0)
ON CONFLICT DO NOTHING;

-- ---- Products & parts & the BOM tree ---------------------------------------
-- PRD-GEARBOX-X1 = housing + 2x gear-assembly; gear-assembly = gear + 2x bearing.
INSERT INTO product (product_id, name, spec) VALUES
  ('PRD-GEARBOX-X1', 'Gearbox X1', '{"ratio":"4.1:1","torque_nm":320,"line":"stamping"}'),
  ('PRD-AXLE-A2',    'Axle A2',    '{"length_mm":1420,"material":"forged-steel"}')
ON CONFLICT (product_id) DO NOTHING;

INSERT INTO part (part_id, name, part_type, spec) VALUES
  ('PT-HOUSING-GX', 'Gearbox Housing GX', 'housing',  '{"material":"aluminum","weight_kg":6.2}'),
  ('PT-GEAR-ASSY',  'Gear Assembly',      'assembly', '{"teeth":42}'),
  ('PT-GEAR-42T',   'Gear 42T',           'gear',     '{"teeth":42,"material":"hardened-steel"}'),
  ('PT-BEARING-6204','Bearing 6204',      'bearing',  '{"bore_mm":20,"seals":"2RS","rated_rpm":14000}'),
  ('PT-BOLT-M8',    'Bolt M8x30',         'fastener', '{"thread":"M8","len_mm":30,"grade":"8.8"}')
ON CONFLICT (part_id) DO NOTHING;

INSERT INTO bom_edge (parent_id, child_part, qty) VALUES
  ('PRD-GEARBOX-X1', 'PT-HOUSING-GX',   1),
  ('PRD-GEARBOX-X1', 'PT-GEAR-ASSY',    2),
  ('PRD-GEARBOX-X1', 'PT-BOLT-M8',      8),
  ('PT-GEAR-ASSY',   'PT-GEAR-42T',     1),
  ('PT-GEAR-ASSY',   'PT-BEARING-6204', 2)
ON CONFLICT (parent_id, child_part) DO NOTHING;

-- ---- Work orders & operations (MES) ----------------------------------------
INSERT INTO work_order (wo_id, plant_id, product_id, qty, status, due_ts) VALUES
  ('WO-8821', 'PL-DETROIT', 'PRD-GEARBOX-X1', 50, 'released',    now() + interval '2 days'),
  ('WO-8822', 'PL-AUSTIN',  'PRD-AXLE-A2',   120, 'in_progress', now() + interval '1 day')
ON CONFLICT (wo_id) DO NOTHING;

INSERT INTO operation (op_id, wo_id, machine_id, seq, status, starts_at, ends_at) VALUES
  ('OP-1', 'WO-8821', 'M-204', 1, 'pending', now() + interval '1 hour', now() + interval '3 hour'),
  ('OP-2', 'WO-8821', 'M-205', 2, 'pending', now() + interval '3 hour', now() + interval '4 hour'),
  ('OP-3', 'WO-8822', 'M-310', 1, 'in_progress', now(),                 now() + interval '2 hour')
ON CONFLICT (op_id) DO NOTHING;

-- ---- Supply chain ----------------------------------------------------------
INSERT INTO supplier (supplier_id, name, lat, lon, spec) VALUES
  ('SUP-BEARINGCO', 'BearingCo',      41.8781, -87.6298, '{"lead_time_weeks":6,"quality_ppm":45,"dual_source":true}'),
  ('SUP-GEARWORKS', 'GearWorks GmbH', 48.7758,   9.1829, '{"lead_time_weeks":9,"quality_ppm":20,"dual_source":false}'),
  ('SUP-FASTENALL', 'FastenAll',      33.7490, -84.3880, '{"lead_time_weeks":2,"quality_ppm":120,"dual_source":true}')
ON CONFLICT (supplier_id) DO NOTHING;

INSERT INTO warehouse (warehouse_id, plant_id, lat, lon, capacity) VALUES
  ('WH-DET-1', 'PL-DETROIT', 42.3400, -83.0500, 100000),
  ('WH-AUS-1', 'PL-AUSTIN',  30.2700, -97.7400,  80000)
ON CONFLICT (warehouse_id) DO NOTHING;

INSERT INTO inventory (part_id, warehouse_id, qty) VALUES
  ('PT-BEARING-6204', 'WH-DET-1', 1800),
  ('PT-GEAR-42T',     'WH-DET-1',  240),
  ('PT-HOUSING-GX',   'WH-DET-1',  120),
  ('PT-BOLT-M8',      'WH-DET-1', 9000),
  ('PT-BEARING-6204', 'WH-AUS-1',  600)
ON CONFLICT (part_id, warehouse_id) DO NOTHING;

INSERT INTO part_supplier (part_id, supplier_id, lead_time_weeks) VALUES
  ('PT-BEARING-6204', 'SUP-BEARINGCO', 6),
  ('PT-GEAR-42T',     'SUP-GEARWORKS', 9),
  ('PT-BOLT-M8',      'SUP-FASTENALL', 2)
ON CONFLICT (part_id, supplier_id) DO NOTHING;

-- ---- Maintenance write-ups (raw; AI journeys extract structure) ------------
INSERT INTO maintenance_log (machine_id, ts, writeup) VALUES
  ('M-204', now() - interval '3 day',  'Operator reports intermittent knocking on the press ram during downstroke. Vibration trending up over the shift. Suspect worn guide bearing, recommend inspection.'),
  ('M-421', now() - interval '1 day',  'CNC spindle running hot, thermal alarm at 71C. Coolant flow looks low. Cleaned filter, still derated. Needs pump check.'),
  ('M-311', now() - interval '6 day',  'Scheduled PM. Replaced tool holder, recalibrated axis. All within spec after.'),
  ('M-101', now() - interval '12 day', 'Minor hydraulic seep at the manifold. Torqued fittings, monitoring.')
ON CONFLICT DO NOTHING;
