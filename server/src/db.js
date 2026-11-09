// Azure SQL access. In Azure the Container App's managed identity signs in (no passwords).
// Locally, DefaultAzureCredential uses your `az login`. DB_CONNECTION_STRING overrides both.
const sql = require('mssql');
const fs = require('fs');
const path = require('path');

let poolPromise = null;
let lastError = null;

function config() {
  if (process.env.DB_CONNECTION_STRING) return process.env.DB_CONNECTION_STRING;
  if (!process.env.DB_SERVER || !process.env.DB_NAME) return null;
  return {
    server: process.env.DB_SERVER,
    database: process.env.DB_NAME,
    options: { encrypt: true, trustServerCertificate: false },
    authentication: { type: 'azure-active-directory-default', options: {} },
    pool: { max: 5, min: 0, idleTimeoutMillis: 60000 },
    connectionTimeout: 60000,
    requestTimeout: 30000
  };
}

const sleep = ms => new Promise(r => setTimeout(r, ms));

// Serverless databases auto-pause; the first connection wakes them (can take ~1 minute).
async function connectWithRetry(cfg) {
  let delay = 3000;
  for (let attempt = 1; attempt <= 8; attempt++) {
    try {
      const pool = await new sql.ConnectionPool(cfg).connect();
      lastError = null;
      return pool;
    } catch (e) {
      lastError = e;
      console.warn(`[db] connect attempt ${attempt} failed: ${e.code || ''} ${e.message}`);
      await sleep(delay);
      delay = Math.min(delay * 2, 20000);
    }
  }
  throw lastError;
}

function getPool() {
  const cfg = config();
  if (!cfg) return Promise.reject(new Error('Database not configured (set DB_SERVER and DB_NAME)'));
  if (!poolPromise) {
    poolPromise = connectWithRetry(cfg).then(async pool => { await migrate(pool); return pool; })
      .catch(e => { poolPromise = null; throw e; });
  }
  return poolPromise;
}

async function migrate(pool) {
  await pool.request().batch(`IF OBJECT_ID('dbo.schema_migrations') IS NULL
    CREATE TABLE dbo.schema_migrations (version INT PRIMARY KEY, applied_at DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME());`);
  const done = new Set((await pool.request().query('SELECT version FROM dbo.schema_migrations')).recordset.map(r => r.version));
  const dir = path.join(__dirname, 'migrations');
  const files = fs.readdirSync(dir).filter(f => /^\d+_.*\.sql$/.test(f)).sort();
  for (const f of files) {
    const v = parseInt(f, 10);
    if (done.has(v)) continue;
    const tx = new sql.Transaction(pool);
    await tx.begin();
    try {
      await new sql.Request(tx).batch(fs.readFileSync(path.join(dir, f), 'utf8'));
      await new sql.Request(tx).input('v', sql.Int, v).query('INSERT INTO dbo.schema_migrations (version) VALUES (@v)');
      await tx.commit();
      console.log(`[db] applied migration ${f}`);
    } catch (e) {
      await tx.rollback();
      throw e;
    }
  }
}

module.exports = { sql, getPool, configured: () => !!config(), lastError: () => lastError };
