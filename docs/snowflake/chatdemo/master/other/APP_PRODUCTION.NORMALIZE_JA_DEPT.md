---
type: other
schema_id: SCH_20251225131727
physical: NORMALIZE_JA_DEPT
object_type: function
comment: RAWデータ格納用ステージ
---

# SQL
```sql
create or replace function APP_PRODUCTION.NORMALIZE_JA_DEPT(s string)
returns string
language javascript
as
$$
  var s0 = arguments[0];
  if (s0 === null) return null;
  let t = String(s0);
  t = t.normalize("NFKC");
  t = t.trim().toLowerCase();
  t = t.replace(/(株式会社|有限会社|合同会社|（株）|\(株\)|㈱|（有）|\(有\)|㈲|（同）|\(同\))/g, "");
  t = t.replace(/[\s\u3000]+/g, "");
  t = t.replace(/[()\[\]{}<>「」『』【】（）・,，．.／\/\\\-＿_―ー…:：;；!！?？'"“”‘’&＋+*＝=]/g, "");
  t = t.replace(/[\u3041-\u3096]/g, function (ch) {
    return String.fromCharCode(ch.charCodeAt(0) + 0x60);
  });
  t = t.replace(/(?<!本)(部|課|室|グループ|G|ユニット|チーム)$/g, "");
  return t;
$$;
```

