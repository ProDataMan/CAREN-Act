-- Volunteer narrations of Learn lessons: a link to the recording plus credit and license, reviewed by an editor.
CREATE TABLE dbo.narrations (
  id INT IDENTITY(1,1) PRIMARY KEY,
  created_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
  module_id NVARCHAR(40) NOT NULL,
  lang CHAR(2) NOT NULL,
  credit_name NVARCHAR(80) NOT NULL,
  contact_email NVARCHAR(320) NULL,
  file_url NVARCHAR(500) NOT NULL,
  license NVARCHAR(20) NOT NULL,
  status NVARCHAR(20) NOT NULL DEFAULT 'new'
);
