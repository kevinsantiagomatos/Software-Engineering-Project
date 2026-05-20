CREATE TABLE IF NOT EXISTS policy_definition (
  policy_id VARCHAR(64) NOT NULL,
  label VARCHAR(255) NOT NULL,
  file_path VARCHAR(512) NOT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  updated_by VARCHAR(255) DEFAULT NULL,
  PRIMARY KEY (policy_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO policy_definition (policy_id, label, file_path, updated_by)
VALUES
  ('company_policies', 'Company Policies', 'policies/company_policies.pdf', 'migration_20260519'),
  ('medical_plan', 'Medical Plan Policy', 'policies/medical_plan_policy.pdf', 'migration_20260519')
ON DUPLICATE KEY UPDATE
  label = VALUES(label),
  file_path = VALUES(file_path);
