CREATE TABLE dbo.users (
  id INT IDENTITY(1,1) PRIMARY KEY,
  provider NVARCHAR(20) NOT NULL,
  provider_id NVARCHAR(200) NOT NULL,
  email NVARCHAR(320) NULL,
  name NVARCHAR(200) NULL,
  picture NVARCHAR(1000) NULL,
  created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
  last_login_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
  CONSTRAINT uq_users_provider UNIQUE (provider, provider_id)
);

CREATE TABLE dbo.sessions (
  id CHAR(64) PRIMARY KEY,
  user_id INT NOT NULL REFERENCES dbo.users(id) ON DELETE CASCADE,
  created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
  expires_at DATETIME2 NOT NULL
);
CREATE INDEX ix_sessions_user ON dbo.sessions(user_id);

CREATE TABLE dbo.volunteers (
  id INT IDENTITY(1,1) PRIMARY KEY,
  created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
  user_id INT NULL REFERENCES dbo.users(id) ON DELETE SET NULL,
  name NVARCHAR(200) NOT NULL,
  email NVARCHAR(320) NOT NULL,
  phone NVARCHAR(50) NULL,
  state CHAR(2) NOT NULL,
  area NVARCHAR(200) NULL,
  roles NVARCHAR(400) NOT NULL,
  background NVARCHAR(100) NULL,
  hours NVARCHAR(50) NULL,
  experience NVARCHAR(2000) NULL,
  status NVARCHAR(20) NOT NULL DEFAULT 'new',
  source NVARCHAR(40) NOT NULL DEFAULT 'web'
);
CREATE INDEX ix_volunteers_state ON dbo.volunteers(state);
