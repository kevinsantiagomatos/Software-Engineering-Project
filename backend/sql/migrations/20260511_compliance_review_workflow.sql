-- Compliance review workflow table

CREATE TABLE IF NOT EXISTS compliance_review_item (
  id BIGINT NOT NULL AUTO_INCREMENT,
  email VARCHAR(255) NOT NULL,
  check_key VARCHAR(64) NOT NULL,
  check_label VARCHAR(255) NOT NULL,
  state VARCHAR(32) NOT NULL DEFAULT 'pending_review',
  reviewer_note TEXT DEFAULT NULL,
  reviewed_by VARCHAR(255) DEFAULT NULL,
  reviewed_at DATETIME(6) DEFAULT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  updated_by VARCHAR(255) DEFAULT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_compliance_email_key (email, check_key),
  KEY idx_compliance_email_state (email, state),
  KEY idx_compliance_email_updated (email, updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
