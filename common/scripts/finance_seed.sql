-- ============================================================================
-- Seed data for the Bank running example. Small, hand-built, legible so you can
-- reason about query results. Journeys that need scale (pg-explain, pg-index,
-- pg-partition) generate their own data on top of this.
-- Loaded by common/scripts/load_bank.py after finance_schema.sql.
-- ============================================================================
SET search_path TO bank, public;

-- ---- Branches (3 branches, 2 business units) --------------------------------
INSERT INTO branch (branch_id, name, region, operator, lat, lon) VALUES
  ('BR-NYC',    'New York Midtown',  'US-Northeast', 'RetailBank',   40.7549, -73.9840),
  ('BR-SFO',    'San Francisco FiDi', 'US-West',     'RetailBank',   37.7946, -122.3999),
  ('BR-LON',    'London City',       'EU-UK',        'GlobalMarkets', 51.5155,  -0.0922)
ON CONFLICT (branch_id) DO NOTHING;

-- ---- Accounts (a few per branch, on named product lines) --------------------
INSERT INTO account (account_id, branch_id, line, type, status, health_pct) VALUES
  ('ACCT-100234', 'BR-NYC', 'Checking', 'retail',     'good_standing', 98.5),
  ('ACCT-100235', 'BR-NYC', 'Savings',  'retail',     'good_standing', 96.2),
  ('ACCT-100240', 'BR-NYC', 'Credit',   'retail',     'watch',         91.0),
  ('ACCT-100241', 'BR-NYC', 'Checking', 'commercial', 'good_standing', 99.1),
  ('ACCT-200310', 'BR-SFO', 'Wealth',   'wealth',     'good_standing', 94.7),
  ('ACCT-200311', 'BR-SFO', 'Credit',   'retail',     'frozen',        88.0),
  ('ACCT-300420', 'BR-LON', 'Checking', 'commercial', 'good_standing', 97.3),
  ('ACCT-300421', 'BR-LON', 'Wealth',   'wealth',     'watch',         82.4)
ON CONFLICT (account_id) DO NOTHING;

-- ---- A few transactions per account (journeys generate more as needed) ------
INSERT INTO txn (account_id, ts, amount_usd, anomaly_score, mcc, util_pct) VALUES
  ('ACCT-100240', now() - interval '10 min',  120.50, 2.1, 5411, 74.0),
  ('ACCT-100240', now() - interval  '5 min',  340.00, 2.4, 5812, 76.5),
  ('ACCT-100240', now() - interval  '1 min', 2200.00, 8.7, 6011, 92.0),   -- anomaly spiking
  ('ACCT-300421', now() - interval  '5 min', 9800.00, 5.6, 4829, 91.0),   -- watch account, large wire
  ('ACCT-100234', now() - interval  '5 min',   42.00, 1.2, 5814, 60.0)
ON CONFLICT DO NOTHING;

-- ---- Funds, instruments, and the holdings tree ------------------------------
-- FUND-GROWTH-A = cash + 2x SLEEVE-EQ; SLEEVE-EQ = AAPL + 2x UST-10Y.
INSERT INTO fund (fund_id, name, spec) VALUES
  ('FUND-GROWTH-A', 'Growth Fund A', '{"mandate":"growth","risk":"high","base_ccy":"USD"}'),
  ('FUND-INCOME-B', 'Income Fund B', '{"mandate":"income","risk":"low","base_ccy":"USD"}')
ON CONFLICT (fund_id) DO NOTHING;

INSERT INTO instrument (instrument_id, name, kind, spec) VALUES
  ('INS-CASH-USD', 'US Dollar Cash',      'cash',   '{"ccy":"USD"}'),
  ('INS-SLEEVE-EQ','Equity Sleeve',       'etf',    '{"theme":"large-cap"}'),
  ('INS-AAPL',     'Apple Inc',           'equity', '{"ticker":"AAPL","sector":"tech","beta":1.2}'),
  ('INS-UST-10Y',  'US Treasury 10Y',     'bond',   '{"tenor":"10Y","coupon":4.0,"rating":"AAA"}'),
  ('INS-MSFT',     'Microsoft Corp',      'equity', '{"ticker":"MSFT","sector":"tech","beta":0.9}')
ON CONFLICT (instrument_id) DO NOTHING;

INSERT INTO holding (parent_id, instrument_id, qty) VALUES
  ('FUND-GROWTH-A',  'INS-CASH-USD',  1),
  ('FUND-GROWTH-A',  'INS-SLEEVE-EQ', 2),
  ('FUND-GROWTH-A',  'INS-MSFT',      8),
  ('INS-SLEEVE-EQ',  'INS-AAPL',      1),
  ('INS-SLEEVE-EQ',  'INS-UST-10Y',   2)
ON CONFLICT (parent_id, instrument_id) DO NOTHING;

-- ---- Trades & settlements ---------------------------------------------------
INSERT INTO trade (trade_id, branch_id, fund_id, qty, status, due_ts) VALUES
  ('TRD-8821', 'BR-NYC', 'FUND-GROWTH-A', 50,  'placed',    now() + interval '2 days'),
  ('TRD-8822', 'BR-SFO', 'FUND-INCOME-B', 120, 'executing', now() + interval '1 day')
ON CONFLICT (trade_id) DO NOTHING;

INSERT INTO settlement (settlement_id, trade_id, account_id, seq, status, starts_at, ends_at) VALUES
  ('STL-1', 'TRD-8821', 'ACCT-100240', 1, 'pending',     now() + interval '1 hour', now() + interval '3 hour'),
  ('STL-2', 'TRD-8821', 'ACCT-100241', 2, 'pending',     now() + interval '3 hour', now() + interval '4 hour'),
  ('STL-3', 'TRD-8822', 'ACCT-200310', 1, 'in_progress', now(),                     now() + interval '2 hour')
ON CONFLICT (settlement_id) DO NOTHING;

-- ---- Counterparties & custody -----------------------------------------------
INSERT INTO counterparty (counterparty_id, name, lat, lon, spec) VALUES
  ('CP-GOLDMAN',  'Goldman Sachs',   40.7145, -74.0140, '{"credit_rating":"A+","exposure_limit_m":500,"dual_source":true}'),
  ('CP-BARCLAYS', 'Barclays',        51.5049,  -0.0196, '{"credit_rating":"A","exposure_limit_m":300,"dual_source":false}'),
  ('CP-CITADEL',  'Citadel Sec',     41.8858, -87.6229, '{"credit_rating":"A-","exposure_limit_m":250,"dual_source":true}')
ON CONFLICT (counterparty_id) DO NOTHING;

INSERT INTO custodian (custodian_id, branch_id, lat, lon, capacity) VALUES
  ('CUST-BNY', 'BR-NYC', 40.7128, -74.0060, 100000),
  ('CUST-STT', 'BR-SFO', 37.7749, -122.4194, 80000)
ON CONFLICT (custodian_id) DO NOTHING;

INSERT INTO position (instrument_id, custodian_id, qty) VALUES
  ('INS-AAPL',    'CUST-BNY', 1800),
  ('INS-UST-10Y', 'CUST-BNY',  240),
  ('INS-MSFT',    'CUST-BNY',  120),
  ('INS-CASH-USD','CUST-BNY', 9000),
  ('INS-AAPL',    'CUST-STT',  600)
ON CONFLICT (instrument_id, custodian_id) DO NOTHING;

INSERT INTO trade_counterparty (instrument_id, counterparty_id, settle_days) VALUES
  ('INS-AAPL',    'CP-GOLDMAN',  2),
  ('INS-UST-10Y', 'CP-BARCLAYS', 1),
  ('INS-MSFT',    'CP-CITADEL',  2)
ON CONFLICT (instrument_id, counterparty_id) DO NOTHING;

-- ---- Case notes (raw analyst notes; AI journeys extract structure) ----------
INSERT INTO case_note (account_id, ts, writeup) VALUES
  ('ACCT-100240', now() - interval '3 day',  'Cardholder reports three card-not-present charges to an overseas merchant they do not recognize; velocity spike overnight. Suspect card compromise, recommend freeze and reissue.'),
  ('ACCT-300421', now() - interval '1 day',  'Large outbound wire to a new beneficiary in a high-risk jurisdiction, just under the reporting threshold. Structuring pattern? Needs AML review.'),
  ('ACCT-200311', now() - interval '6 day',  'Customer disputed a recurring subscription charge. Confirmed merchant error, refunded, closed.'),
  ('ACCT-100234', now() - interval '12 day', 'Minor address-mismatch flag on a low-value transaction. Verified with customer, cleared.')
ON CONFLICT DO NOTHING;
