-- Role/department normalization for user model
-- Canonical roles: employee, contractor, manager, admin, superadmin

CREATE TABLE IF NOT EXISTS role (
  id BIGINT NOT NULL AUTO_INCREMENT,
  name VARCHAR(64) NOT NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (id),
  UNIQUE KEY uq_role_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO role (name, is_active, created_at)
VALUES
  ('employee', 1, NOW()),
  ('contractor', 1, NOW()),
  ('manager', 1, NOW()),
  ('admin', 1, NOW()),
  ('superadmin', 1, NOW())
ON DUPLICATE KEY UPDATE is_active = VALUES(is_active);

ALTER TABLE `user`
  ADD COLUMN IF NOT EXISTS role_id BIGINT NULL AFTER role,
  ADD COLUMN IF NOT EXISTS department_id BIGINT NULL AFTER department;

ALTER TABLE `user`
  ADD KEY IF NOT EXISTS idx_user_role_id (role_id),
  ADD KEY IF NOT EXISTS idx_user_department_id (department_id);

-- Convert legacy departmental roles to admin
UPDATE `user`
SET role = CASE
  WHEN LOWER(role) IN ('hr', 'it', 'compliance') THEN 'admin'
  WHEN LOWER(role) IN ('employee','contractor','manager','admin','superadmin') THEN LOWER(role)
  ELSE 'employee'
END
WHERE id IS NOT NULL;

-- Best-effort backfill of department for legacy users
UPDATE `user`
SET department = 'HR'
WHERE id IS NOT NULL AND LOWER(role)='admin' AND (department IS NULL OR department='') AND LOWER(email) LIKE '%hr%';

UPDATE `user`
SET department = 'IT'
WHERE id IS NOT NULL AND LOWER(role)='admin' AND (department IS NULL OR department='') AND LOWER(email) LIKE '%it%';

UPDATE `user`
SET department = 'Compliance'
WHERE id IS NOT NULL AND LOWER(role)='admin' AND (department IS NULL OR department='') AND LOWER(email) LIKE '%compliance%';

UPDATE `user` u
LEFT JOIN role r ON LOWER(r.name)=LOWER(u.role)
SET u.role_id = r.id
WHERE u.id IS NOT NULL AND (u.role_id IS NULL OR u.role_id = 0);

UPDATE `user` u
LEFT JOIN department d ON LOWER(d.name)=LOWER(u.department)
SET u.department_id = d.id
WHERE u.id IS NOT NULL AND (u.department_id IS NULL OR u.department_id = 0);

-- Superadmin has no department
UPDATE `user`
SET department = NULL, department_id = NULL
WHERE id IS NOT NULL AND LOWER(role)='superadmin';
