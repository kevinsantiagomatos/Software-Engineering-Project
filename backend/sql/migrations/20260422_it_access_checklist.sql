-- Granular IT access checklist model (card/checkmark workflow)
-- States:
--   not_configured
--   configured_pending_confirmation
--   configured_confirmed
--   configured_declined
--   configured_error

CREATE TABLE IF NOT EXISTS it_access_item (
  id BIGINT NOT NULL AUTO_INCREMENT,
  email VARCHAR(255) NOT NULL,
  access_key VARCHAR(64) NOT NULL,
  access_title VARCHAR(255) NOT NULL,
  state VARCHAR(48) NOT NULL DEFAULT 'not_configured',
  details TEXT DEFAULT NULL,
  portal_url VARCHAR(512) DEFAULT NULL,
  username_hint VARCHAR(255) DEFAULT NULL,
  notes TEXT DEFAULT NULL,
  configured_by VARCHAR(255) DEFAULT NULL,
  configured_at DATETIME(6) DEFAULT NULL,
  hire_response_note TEXT DEFAULT NULL,
  hire_response_at DATETIME(6) DEFAULT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  updated_by VARCHAR(255) DEFAULT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_it_access_email_key (email, access_key),
  KEY idx_it_access_email_state (email, state),
  KEY idx_it_access_email_updated (email, updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Optional compatibility backfill from legacy coarse provisioning table.
-- If the legacy table does not exist, this block becomes a no-op.
SET @legacy_exists := (
  SELECT COUNT(*)
  FROM information_schema.TABLES
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'it_provision'
);

SET @legacy_backfill_sql := IF(
  @legacy_exists = 1,
  "
  INSERT INTO it_access_item (
    email,
    access_key,
    access_title,
    state,
    configured_by,
    configured_at,
    hire_response_at,
    created_at,
    updated_at,
    updated_by
  )
  SELECT
    LOWER(p.email) AS email,
    t.access_key,
    t.access_title,
    'configured_confirmed' AS state,
    'legacy_migration' AS configured_by,
    NOW(6) AS configured_at,
    NOW(6) AS hire_response_at,
    NOW(6) AS created_at,
    NOW(6) AS updated_at,
    'legacy_migration' AS updated_by
  FROM (
    SELECT DISTINCT email
    FROM it_provision
    WHERE email IS NOT NULL AND email <> ''
  ) p
  CROSS JOIN (
    SELECT 'laptop_intune' AS access_key, 'Configure laptop with Intune and required apps' AS access_title
    UNION ALL SELECT 'm365_account', 'Create Microsoft 365 account + Out of Office'
    UNION ALL SELECT 'quickbooks_time', 'Grant QuickBooks Time access (@paoli.io)'
    UNION ALL SELECT 'slack_access', 'Add to Slack with SSO'
    UNION ALL SELECT 'atlassian_access', 'Add to Jira & Confluence (SSO)'
    UNION ALL SELECT 'client_access', 'Provision client/project access'
  ) t
  ON DUPLICATE KEY UPDATE
    access_title = VALUES(access_title)
  ",
  "SELECT 1"
);

PREPARE legacy_stmt FROM @legacy_backfill_sql;
EXECUTE legacy_stmt;
DEALLOCATE PREPARE legacy_stmt;
