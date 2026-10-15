-- ============================================================================
-- Seed data for the Bank running example (Mexico data). Small, hand-built,
-- legible so you can reason about query results. Journeys that need scale
-- (pg-explain, pg-index, pg-partition) generate their own data on top of this.
-- Loaded by common/scripts/load_bank.py after finance_schema.sql.
--
-- Amounts are in MXN. Every institution (counterparties, custodians, listed
-- companies) is fictional. CLABEs are synthetic: bank code 999 (fictional),
-- a real plaza code (CDMX 180, Monterrey 580, Guadalajara 320), the account
-- number, and a valid check digit. They are not real accounts.
-- ============================================================================
SET search_path TO bank, public;

-- ---- Branches (3 branches, 2 business units) --------------------------------
INSERT INTO branch (branch_id, name, region, operator, lat, lon) VALUES
  ('BR-CDMX', 'CDMX Reforma',            'MX-Centro',    'RetailBank',    19.4270,  -99.1677),
  ('BR-MTY',  'Monterrey San Pedro',     'MX-Noreste',   'RetailBank',    25.6514, -100.4020),
  ('BR-GDL',  'Guadalajara Chapultepec', 'MX-Occidente', 'GlobalMarkets', 20.6736, -103.3700)
ON CONFLICT (branch_id) DO NOTHING;

-- ---- Accounts (a few per branch, on named product lines) --------------------
INSERT INTO account (account_id, branch_id, line, type, status, health_pct, clabe) VALUES
  ('CTA-100234', 'BR-CDMX', 'Checking', 'retail',     'good_standing', 98.5, '999180000001002342'),
  ('CTA-100235', 'BR-CDMX', 'Savings',  'retail',     'good_standing', 96.2, '999180000001002355'),
  ('CTA-100240', 'BR-CDMX', 'Credit',   'retail',     'watch',         91.0, '999180000001002407'),
  ('CTA-100241', 'BR-CDMX', 'Checking', 'commercial', 'good_standing', 99.1, '999180000001002410'),
  ('CTA-200310', 'BR-MTY',  'Wealth',   'wealth',     'good_standing', 94.7, '999580000002003102'),
  ('CTA-200311', 'BR-MTY',  'Credit',   'retail',     'frozen',        88.0, '999580000002003115'),
  ('CTA-300420', 'BR-GDL',  'Checking', 'commercial', 'good_standing', 97.3, '999320000003004205'),
  ('CTA-300421', 'BR-GDL',  'Wealth',   'wealth',     'watch',         82.4, '999320000003004218')
ON CONFLICT (account_id) DO NOTHING;

-- ---- A few transactions per account (journeys generate more as needed) ------
-- SPEI transfers have no merchant category code (mcc), so it is NULL for them.
INSERT INTO txn (account_id, ts, amount, currency, channel, anomaly_score, mcc, util_pct) VALUES
  ('CTA-100240', now() - interval '10 min',   2150.00, 'MXN', 'tarjeta', 2.1, 5411, 74.0),  -- groceries, card
  ('CTA-100240', now() - interval  '5 min',   5980.00, 'MXN', 'tarjeta', 2.4, 5812, 76.5),  -- restaurant, card
  ('CTA-100240', now() - interval  '1 min',  38500.00, 'MXN', 'SPEI',    8.7, NULL, 92.0),  -- late-night SPEI to a new beneficiary: anomaly spiking
  ('CTA-300421', now() - interval  '5 min', 171500.00, 'MXN', 'SPEI',    5.6, NULL, 91.0),  -- watch account, large transfer
  ('CTA-100234', now() - interval  '5 min',    735.00, 'MXN', 'CoDi',    1.2, 5814, 60.0)   -- small QR payment
ON CONFLICT DO NOTHING;

-- ---- Funds, instruments, and the holdings tree ------------------------------
-- FUND-GROWTH-A = cash + 2x SLEEVE-EQ; SLEEVE-EQ = QTZL + 2x MBONO-10Y.
INSERT INTO fund (fund_id, name, spec) VALUES
  ('FUND-GROWTH-A', 'Growth Fund A', '{"mandate":"growth","risk":"high","base_ccy":"MXN"}'),
  ('FUND-INCOME-B', 'Income Fund B', '{"mandate":"income","risk":"low","base_ccy":"MXN"}')
ON CONFLICT (fund_id) DO NOTHING;

-- Equities are fictional companies. The Bono M is rated on the national (Mexican) scale.
INSERT INTO instrument (instrument_id, name, kind, spec) VALUES
  ('INS-CASH-MXN',  'Mexican Peso Cash',        'cash',   '{"ccy":"MXN"}'),
  ('INS-SLEEVE-EQ', 'Equity Sleeve',            'etf',    '{"theme":"large-cap"}'),
  ('INS-QTZL',      'Quetzal Tecnologia',       'equity', '{"ticker":"QTZL","sector":"tech","beta":1.2}'),
  ('INS-MBONO-10Y', 'Bono M 10Y (Mexico)',      'bond',   '{"tenor":"10Y","coupon":8.5,"rating":"AAA","rating_scale":"national"}'),
  ('INS-ZAFR',      'Zafiro Software',          'equity', '{"ticker":"ZAFR","sector":"tech","beta":0.9}')
ON CONFLICT (instrument_id) DO NOTHING;

INSERT INTO holding (parent_id, instrument_id, qty) VALUES
  ('FUND-GROWTH-A',  'INS-CASH-MXN',  1),
  ('FUND-GROWTH-A',  'INS-SLEEVE-EQ', 2),
  ('FUND-GROWTH-A',  'INS-ZAFR',      8),
  ('INS-SLEEVE-EQ',  'INS-QTZL',      1),
  ('INS-SLEEVE-EQ',  'INS-MBONO-10Y', 2)
ON CONFLICT (parent_id, instrument_id) DO NOTHING;

-- ---- Trades & settlements ---------------------------------------------------
INSERT INTO trade (trade_id, branch_id, fund_id, qty, status, due_ts) VALUES
  ('TRD-8821', 'BR-CDMX', 'FUND-GROWTH-A', 50,  'placed',    now() + interval '2 days'),
  ('TRD-8822', 'BR-MTY',  'FUND-INCOME-B', 120, 'executing', now() + interval '1 day')
ON CONFLICT (trade_id) DO NOTHING;

INSERT INTO settlement (settlement_id, trade_id, account_id, seq, status, starts_at, ends_at) VALUES
  ('STL-1', 'TRD-8821', 'CTA-100240', 1, 'pending',     now() + interval '1 hour', now() + interval '3 hour'),
  ('STL-2', 'TRD-8821', 'CTA-100241', 2, 'pending',     now() + interval '3 hour', now() + interval '4 hour'),
  ('STL-3', 'TRD-8822', 'CTA-200310', 1, 'in_progress', now(),                     now() + interval '2 hour')
ON CONFLICT (settlement_id) DO NOTHING;

-- ---- Counterparties & custody (all fictional) ---------------------------------
INSERT INTO counterparty (counterparty_id, name, lat, lon, spec) VALUES
  ('CP-ALTAMAR', 'Altamar Valores',  19.3593,  -99.2595, '{"credit_rating":"A+","exposure_limit_m":500,"dual_source":true}'),
  ('CP-CUMBRE',  'Cumbre Capital',   25.6488, -100.3570, '{"credit_rating":"A","exposure_limit_m":300,"dual_source":false}'),
  ('CP-MIRADOR', 'Mirador Bursatil', 20.6597, -103.3496, '{"credit_rating":"A-","exposure_limit_m":250,"dual_source":true}')
ON CONFLICT (counterparty_id) DO NOTHING;

INSERT INTO custodian (custodian_id, branch_id, lat, lon, capacity) VALUES
  ('CUST-ALTA',  'BR-CDMX', 19.4326,  -99.1332, 100000),
  ('CUST-VALLE', 'BR-MTY',  25.6866, -100.3161,  80000)
ON CONFLICT (custodian_id) DO NOTHING;

INSERT INTO position (instrument_id, custodian_id, qty) VALUES
  ('INS-QTZL',      'CUST-ALTA',  1800),
  ('INS-MBONO-10Y', 'CUST-ALTA',   240),
  ('INS-ZAFR',      'CUST-ALTA',   120),
  ('INS-CASH-MXN',  'CUST-ALTA',  9000),
  ('INS-QTZL',      'CUST-VALLE',  600)
ON CONFLICT (instrument_id, custodian_id) DO NOTHING;

INSERT INTO trade_counterparty (instrument_id, counterparty_id, settle_days) VALUES
  ('INS-QTZL',      'CP-ALTAMAR', 2),
  ('INS-MBONO-10Y', 'CP-CUMBRE',  1),
  ('INS-ZAFR',      'CP-MIRADOR', 2)
ON CONFLICT (instrument_id, counterparty_id) DO NOTHING;

-- ---- Case notes (raw analyst notes; AI journeys extract structure) ----------
INSERT INTO case_note (account_id, ts, writeup) VALUES
  ('CTA-100240', now() - interval '3 day',  'Cardholder reports three card-not-present charges to a foreign merchant they do not recognize, then a late-night SPEI transfer to a new beneficiary. Suspect account takeover, recommend freeze and card reissue.'),
  ('CTA-300421', now() - interval '1 day',  'Large outbound SPEI transfer to a new beneficiary, just under the internal reporting threshold. Structuring pattern? Needs AML review.'),
  ('CTA-200311', now() - interval '6 day',  'Customer disputed a recurring subscription charge. Confirmed merchant error, refunded, closed.'),
  ('CTA-100234', now() - interval '12 day', 'Minor address-mismatch flag on a low-value CoDi payment. Verified with customer, cleared.')
ON CONFLICT DO NOTHING;
