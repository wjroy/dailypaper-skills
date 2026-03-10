# Published Review Lite (Metadata-First)

> 说明：以下判断仅基于 metadata 与 abstract，不代表全文结论。

## 总览

- active_domain: {{active_domain}}
- input_file: `/tmp/published_lite_50.json`
- reviewed_count: {{reviewed_count}}
- fetch_pdf_count: {{fetch_pdf_count}}
- hold_count: {{hold_count}}
- skip_count: {{skip_count}}

## A. 建议立即获取 PDF (fetch_pdf)

### {{index}}. {{title}}
- decision: `fetch_pdf`
- confidence: {{confidence}}
- why:
  - {{evidence_1}}
  - {{evidence_2}}
- metadata_caveat: {{caveat}}

## B. 观察池 (hold)

### {{index}}. {{title}}
- decision: `hold`
- confidence: {{confidence}}
- why:
  - {{evidence_1}}
  - {{evidence_2}}
- metadata_caveat: {{caveat}}

## C. 暂不跟进 (skip)

### {{index}}. {{title}}
- decision: `skip`
- confidence: {{confidence}}
- why:
  - {{evidence_1}}
  - {{evidence_2}}
- metadata_caveat: {{caveat}}

## JSON 输出字段约定

- `paper_id`
- `review_tier` = `lite`
- `evidence_scope` = `metadata_only`
- `lite_decision` = `fetch_pdf | hold | skip`
- `lite_confidence` (0~1)
- `lite_reasoning` (metadata/abstract evidence only)
- `recommended_for_pdf` (boolean)
