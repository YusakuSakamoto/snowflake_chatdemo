---
type: other
schema_id: SCH_20251226180633
physical: INGEST_VAULT_MD
object_type: procedure
comment:
---

# SQL
```sql
CREATE OR REPLACE PROCEDURE DB_DESIGN.INGEST_VAULT_MD("STAGE_NAME" VARCHAR, "PATTERN" VARCHAR)
RETURNS VARIANT
LANGUAGE PYTHON
RUNTIME_VERSION = '3.11'
PACKAGES = ('snowflake-snowpark-python')
HANDLER = 'run'
EXECUTE AS OWNER
AS '
import hashlib
from snowflake.snowpark.files import SnowflakeFile

BUCKET = "135365622922-snowflake-dbdesign"

def _md5(s: str) -> str:
    return hashlib.md5(s.encode("utf-8")).hexdigest()

def _to_relpath(name: str) -> str:
    """
    LIST結果のnameが
      - s3://<bucket>/path...
      - path...
    のどちらでも、ステージ相対パスを返す。
    """
    n = str(name).lstrip("/")
    prefix = f"s3://{BUCKET}/"
    if n.startswith(prefix):
        return n[len(prefix):]
    # 念のため一般形（s3://bucket/...）も扱う
    if n.startswith("s3://"):
        parts = n.split("/", 3)
        # [''s3:'', '''', ''<bucket>'', ''<rest>'']
        return parts[3] if len(parts) >= 4 else ""
    return n

def run(session, stage_name, pattern):
    rows = session.sql(f"LIST {stage_name} PATTERN=''{pattern}''").collect()

    processed = 0
    errors = 0
    samples = []

    for r in rows:
        try:
            d = r.as_dict()
            full_name = d["name"]
            last_modified = d.get("last_modified", None)

            relpath = _to_relpath(full_name)
            if not relpath:
                raise Exception(f"Could not derive relpath from name={full_name}")

            # scoped url: 第2引数はステージ相対パス
            safe_rel = relpath.replace("''", "''''")
            scoped_url = session.sql(
                f"SELECT BUILD_SCOPED_FILE_URL({stage_name}, ''{safe_rel}'') AS U"
            ).collect()[0]["U"]

            with SnowflakeFile.open(scoped_url, "rb") as f:
                content = f.read().decode("utf-8", errors="replace")

            folder = relpath.split("/", 1)[0] if "/" in relpath else relpath
            doc_id = _md5(relpath)

            session.sql(
                """
MERGE INTO DB_DESIGN.DOCS_OBSIDIAN t
USING (
  SELECT
    ? AS DOC_ID,
    ? AS PATH,
    ? AS FOLDER,
    ? AS CONTENT,
    TRY_TO_TIMESTAMP_TZ(?)::TIMESTAMP_LTZ AS FILE_LAST_MODIFIED
) s
ON t.DOC_ID = s.DOC_ID
WHEN MATCHED AND (
     t.FILE_LAST_MODIFIED IS NULL
  OR s.FILE_LAST_MODIFIED IS NULL
  OR s.FILE_LAST_MODIFIED > t.FILE_LAST_MODIFIED
)
THEN UPDATE SET
  PATH = s.PATH,
  FOLDER = s.FOLDER,
  CONTENT = s.CONTENT,
  FILE_LAST_MODIFIED = s.FILE_LAST_MODIFIED,
  INGESTED_AT = CURRENT_TIMESTAMP()
WHEN NOT MATCHED THEN
  INSERT (DOC_ID, PATH, FOLDER, CONTENT, FILE_LAST_MODIFIED)
  VALUES (s.DOC_ID, s.PATH, s.FOLDER, s.CONTENT, s.FILE_LAST_MODIFIED)
                """,
                params=[doc_id, relpath, folder, content, last_modified]
            ).collect()

            processed += 1

        except Exception as e:
            errors += 1
            if len(samples) < 5:
                samples.append({"error": str(e), "name": d.get("name")})

    return {"files_listed": len(rows), "processed": processed, "errors": errors, "samples": samples}
';
```
