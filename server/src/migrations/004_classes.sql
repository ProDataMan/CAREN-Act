-- Classroom mode: a teacher (signed-in user) creates a class with a join code; students join with a nickname
-- from their browser's anonymous Learn device ID. No student names, emails or accounts are collected.
CREATE TABLE dbo.classes (
  id INT IDENTITY(1,1) PRIMARY KEY,
  code CHAR(6) NOT NULL,
  name NVARCHAR(100) NOT NULL,
  teacher_user_id INT NOT NULL REFERENCES dbo.users(id) ON DELETE CASCADE,
  path_id NVARCHAR(40) NULL,
  created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
  archived BIT NOT NULL DEFAULT 0,
  CONSTRAINT uq_classes_code UNIQUE (code)
);
CREATE TABLE dbo.class_members (
  id INT IDENTITY(1,1) PRIMARY KEY,
  class_id INT NOT NULL REFERENCES dbo.classes(id) ON DELETE CASCADE,
  device_id CHAR(32) NOT NULL,
  nickname NVARCHAR(40) NOT NULL,
  joined_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
  CONSTRAINT uq_class_member UNIQUE (class_id, device_id)
);
CREATE INDEX ix_learn_events_device_only ON dbo.learn_events(device_id) INCLUDE (event_key, xp, created_at);
