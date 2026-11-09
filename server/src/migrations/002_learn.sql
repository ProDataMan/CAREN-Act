-- Learn: progress events (module read, quiz passed, quest done), owned by an anonymous device ID or a signed-in user.
CREATE TABLE dbo.learn_events (
  id INT IDENTITY(1,1) PRIMARY KEY,
  device_id CHAR(32) NULL,
  user_id INT NULL REFERENCES dbo.users(id) ON DELETE CASCADE,
  event_key NVARCHAR(80) NOT NULL,
  xp INT NOT NULL,
  state CHAR(2) NULL,
  created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
);
CREATE INDEX ix_learn_device ON dbo.learn_events(device_id, event_key);
CREATE INDEX ix_learn_user ON dbo.learn_events(user_id, event_key);
CREATE INDEX ix_learn_state ON dbo.learn_events(state) INCLUDE (xp, user_id, device_id);
