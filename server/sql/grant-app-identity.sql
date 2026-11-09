-- Run once in the CAREN_Act database as the Microsoft Entra admin
-- (Azure Portal > SQL databases > CAREN_Act > Query editor > "Continue as <you>").
-- Lets the caren-act-server Container App's managed identity use this database
-- (no password). It cannot touch Ohana_Data or any other database.
IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = 'caren-act-server')
  CREATE USER [caren-act-server] FROM EXTERNAL PROVIDER WITH OBJECT_ID = 'e184de7e-b9a5-41b6-9467-855ad5312ae4';
ALTER ROLE db_datareader ADD MEMBER [caren-act-server];
ALTER ROLE db_datawriter ADD MEMBER [caren-act-server];
ALTER ROLE db_ddladmin  ADD MEMBER [caren-act-server];  -- the app creates its own tables on first start
