---
type: semantic_view
physical: "{{SEMANTIC_VIEW_NAME}}"
comment: "{{DESCRIPTION}}"
---

# {{SEMANTIC_VIEW_NAME}}

## 概要
{{DESCRIPTION}}

## 設計意図
- [[design.{{SEMANTIC_VIEW_NAME}}]] を参照

## YAML定義

```yaml
name: {{SEMANTIC_VIEW_NAME}}
description: {{DESCRIPTION}}

tables:
  - name: {{TABLE_NAME}}
    description: {{TABLE_DESCRIPTION}}
    base_table:
      database: {{DATABASE}}
      schema: {{SCHEMA}}
      table: {{TABLE}}
    primary_key:
      columns: [{{PRIMARY_KEY_COLUMNS}}]
    dimensions:
      - name: {{DIMENSION_NAME}}
        expr: {{DIMENSION_EXPR}}
        data_type: {{DATA_TYPE}}
        description: {{DIMENSION_DESCRIPTION}}
        synonyms: [{{SYNONYMS}}]
    measures:
      - name: {{MEASURE_NAME}}
        expr: {{MEASURE_EXPR}}
        data_type: NUMBER
        description: {{MEASURE_DESCRIPTION}}
        synonyms: [{{SYNONYMS}}]
        default_aggregation: sum

relationships:
  - name: {{RELATIONSHIP_NAME}}
    left_table: {{LEFT_TABLE}}
    right_table: {{RIGHT_TABLE}}
    join_type: left
    join_conditions:
      - left_column: {{LEFT_COLUMN}}
        right_column: {{RIGHT_COLUMN}}
```

## 利用方法

### Cortex Analyst呼び出し
```sql
SELECT SNOWFLAKE.CORTEX.ANALYST_TEXT_TO_SQL(
    @{{SEMANTIC_VIEW_NAME}},
    '自然言語クエリ'
);
```

## 参考リンク
- [[design.{{SEMANTIC_VIEW_NAME}}]] - 設計意図
