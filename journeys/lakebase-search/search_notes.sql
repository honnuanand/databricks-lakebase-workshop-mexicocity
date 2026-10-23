-- ============================================================================
-- Analyst notes for the Lakebase Search journey (40 rows, English).
-- A table of its own, not bank.case_note: Human Review of AI Output replaces the
-- case notes, and in the Agent track it runs before this journey.
--
-- The notes are written so keyword and semantic search disagree: several account
-- takeover notes never use the word "takeover" (new device, SIM swap, changed phone
-- number), and several structuring notes never say "structuring" (many transfers
-- just under the limit). Fixed note_id values make the load safe to rerun.
-- Loaded by journeys/lakebase-search/lakebase_search_databricks(_es).
-- ============================================================================

CREATE TABLE IF NOT EXISTS search_note (
    note_id     INT PRIMARY KEY,
    account_id  TEXT NOT NULL REFERENCES account(account_id),
    category    TEXT NOT NULL,          -- fraud | aml | dispute | phishing | mule | cleared
    ts          TIMESTAMPTZ NOT NULL,
    writeup     TEXT NOT NULL
);

INSERT INTO search_note (note_id, account_id, category, ts, writeup) VALUES
  -- account takeover, said outright
  (1,  'CTA-100240', 'fraud',    now() - interval '2 day',  'Account takeover suspected: password reset, then a SPEI transfer to a new beneficiary within ten minutes.'),
  (2,  'CTA-100234', 'fraud',    now() - interval '5 day',  'Confirmed account takeover. Customer never requested the credential change; access revoked and funds recalled.'),
  -- account takeover, without the word
  (3,  'CTA-100235', 'fraud',    now() - interval '1 day',  'Login from an unrecognized device in another state, followed by a change of the registered phone number.'),
  (4,  'CTA-300420', 'fraud',    now() - interval '3 day',  'Customer says someone else got into the mobile app; the email on file was replaced overnight.'),
  (5,  'CTA-100241', 'fraud',    now() - interval '4 day',  'SIM swap reported by the carrier. One-time codes went to the new SIM and a beneficiary was added.'),
  (6,  'CTA-200310', 'fraud',    now() - interval '8 day',  'Security questions answered correctly by a caller whose voice did not match prior recordings. Online banking locked.'),
  (7,  'CTA-100240', 'fraud',    now() - interval '9 day',  'Session cookies reused from a foreign IP address. Customer was asleep at the time of the activity.'),
  -- structuring / AML, said outright
  (8,  'CTA-300421', 'aml',      now() - interval '1 day',  'Structuring pattern: SPEI transfers just under the internal reporting threshold. Escalated for AML review.'),
  (9,  'CTA-300421', 'aml',      now() - interval '6 day',  'AML review opened for structuring across three accounts owned by the same person.'),
  -- structuring, without the word
  (10, 'CTA-200310', 'aml',      now() - interval '2 day',  'Eleven cash deposits in one week, each a little below the amount that triggers a report.'),
  (11, 'CTA-300420', 'aml',      now() - interval '7 day',  'Many small outgoing transfers to different people on the same day, totaling a large sum.'),
  (12, 'CTA-100241', 'aml',      now() - interval '12 day', 'Funds arrive from a shell company and leave the same afternoon to an exchange abroad.'),
  -- money mules
  (13, 'CTA-100235', 'mule',     now() - interval '3 day',  'Possible money mule: a student account receives transfers from strangers and forwards them within an hour.'),
  (14, 'CTA-300420', 'mule',     now() - interval '10 day', 'Customer was offered a work-from-home job that consisted of receiving and resending payments.'),
  (15, 'CTA-200311', 'mule',     now() - interval '14 day', 'Dormant account suddenly active as a pass-through: incoming CoDi payments, immediate cash withdrawals.'),
  -- card fraud
  (16, 'CTA-100240', 'fraud',    now() - interval '3 day',  'Three card-not-present charges at a foreign online merchant the cardholder does not recognize.'),
  (17, 'CTA-200311', 'fraud',    now() - interval '5 day',  'Card used at two gas stations in different cities twenty minutes apart. Card blocked and reissued.'),
  (18, 'CTA-100234', 'fraud',    now() - interval '11 day', 'Skimming device found at an ATM the customer used; several cards from the same branch affected.'),
  (19, 'CTA-100241', 'fraud',    now() - interval '13 day', 'Small test charges of one peso, then a large electronics purchase on the same card.'),
  -- phishing and social engineering
  (20, 'CTA-100235', 'phishing', now() - interval '2 day',  'Customer clicked a text message link that imitated the bank and typed their card number on the fake page.'),
  (21, 'CTA-300421', 'phishing', now() - interval '4 day',  'Caller posing as bank security asked the customer to move money to a safe account. Customer complied.'),
  (22, 'CTA-200310', 'phishing', now() - interval '9 day',  'Fake invoice email from a supplier changed the CLABE for payment. Commercial client paid the wrong account.'),
  (23, 'CTA-100234', 'phishing', now() - interval '15 day', 'Customer received a call about a prize and read out the one-time code sent to their phone.'),
  -- disputes and chargebacks
  (24, 'CTA-200311', 'dispute',  now() - interval '6 day',  'Customer disputed a recurring subscription charge. Confirmed merchant error, refunded, closed.'),
  (25, 'CTA-100240', 'dispute',  now() - interval '7 day',  'Chargeback filed for a hotel stay that was cancelled within the free cancellation window.'),
  (26, 'CTA-300420', 'dispute',  now() - interval '16 day', 'Customer charged twice for the same restaurant bill. Duplicate reversed by the merchant.'),
  (27, 'CTA-100241', 'dispute',  now() - interval '18 day', 'Goods never delivered by an online store; customer requests a chargeback after thirty days.'),
  (28, 'CTA-100235', 'dispute',  now() - interval '20 day', 'Customer claims the ATM did not dispense cash but the withdrawal posted. Journal review pending.'),
  -- SPEI and CoDi operational issues
  (29, 'CTA-100234', 'cleared',  now() - interval '1 day',  'SPEI transfer returned by the receiving bank because the CLABE had a typo. Customer resent it correctly.'),
  (30, 'CTA-300421', 'cleared',  now() - interval '5 day',  'Large SPEI payment to a known supplier flagged by amount only. Matches the monthly invoice; cleared.'),
  (31, 'CTA-200310', 'cleared',  now() - interval '8 day',  'CoDi payment request rejected twice because of a network timeout. Third attempt succeeded.'),
  -- false positives
  (32, 'CTA-100234', 'cleared',  now() - interval '12 day', 'Minor address-mismatch flag on a low-value CoDi payment. Verified with customer, cleared.'),
  (33, 'CTA-100241', 'cleared',  now() - interval '3 day',  'Travel notice on file explains card purchases in Madrid. Alert closed as a false positive.'),
  (34, 'CTA-300420', 'cleared',  now() - interval '6 day',  'Payroll run triggered a velocity alert: two hundred transfers to employees. Expected, cleared.'),
  (35, 'CTA-200310', 'cleared',  now() - interval '10 day', 'New phone set up by the customer in the branch, identity checked in person. Device change approved.'),
  (36, 'CTA-100235', 'cleared',  now() - interval '17 day', 'Login from a new laptop confirmed by the customer through the app. No further action.'),
  -- lending and other
  (37, 'CTA-300421', 'fraud',    now() - interval '4 day',  'Loan application with a pay stub that does not match the employer records. Identity documents look edited.'),
  (38, 'CTA-200311', 'fraud',    now() - interval '9 day',  'Synthetic identity suspected: real CURP, made-up name and address, credit file only two months old.'),
  (39, 'CTA-100240', 'aml',      now() - interval '19 day', 'Customer cannot explain the source of a large deposit; asked for supporting documents.'),
  (40, 'CTA-300420', 'cleared',  now() - interval '21 day', 'Elderly customer withdrew savings for a family wedding; branch manager spoke with them, no coercion.')
ON CONFLICT (note_id) DO NOTHING;
