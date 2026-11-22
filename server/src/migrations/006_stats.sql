-- Privacy-respecting usage counts: daily totals only. No IP addresses, cookies, device IDs or user IDs.
CREATE TABLE dbo.stats_daily (
  day DATE NOT NULL,
  kind NVARCHAR(12) NOT NULL,   -- page | event | ref
  name NVARCHAR(100) NOT NULL,  -- page file, event name (e.g. read:rights), or referring site
  lang CHAR(2) NOT NULL,
  n INT NOT NULL,
  CONSTRAINT pk_stats_daily PRIMARY KEY (day, kind, name, lang)
);
