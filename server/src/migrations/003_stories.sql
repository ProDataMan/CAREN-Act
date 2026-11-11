-- First-person stories and oral histories, published only after an editor approves them.
CREATE TABLE dbo.stories (
  id INT IDENTITY(1,1) PRIMARY KEY,
  created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
  user_id INT NULL REFERENCES dbo.users(id) ON DELETE SET NULL,
  display_name NVARCHAR(80) NOT NULL,
  state CHAR(2) NULL,
  place NVARCHAR(120) NULL,
  topic NVARCHAR(40) NOT NULL,
  title NVARCHAR(160) NOT NULL,
  body NVARCHAR(MAX) NOT NULL,
  told_by NVARCHAR(20) NOT NULL,
  media_url NVARCHAR(500) NULL,
  lang CHAR(2) NOT NULL DEFAULT 'en',
  contact_email NVARCHAR(320) NULL,
  status NVARCHAR(20) NOT NULL DEFAULT 'new',
  approved_at DATETIME2 NULL
);
CREATE INDEX ix_stories_status ON dbo.stories(status, approved_at);
