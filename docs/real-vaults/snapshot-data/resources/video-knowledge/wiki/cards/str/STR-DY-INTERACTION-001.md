---
card_id: "STR-DY-INTERACTION-001"
type: "STR"
status: "active"
version: "1.0.0"
payload_digest: "sha256:4f12a116a3906edd9b209b7e1b533354d8cadb96e0bc063210ca71821112331c"
transaction_id: "dy-adp-20260930-1"
source_record_id: "SRC-DY-a37a1d6542469a4bc20707ba"
---
```json
{
  "schema_version": "structure-card/v2",
  "card_id": "STR-DY-INTERACTION-001",
  "card_type": "STR",
  "version": "1.0.0",
  "status": "active",
  "source_ids": [
    "SRC-DY-a37a1d6542469a4bc20707ba"
  ],
  "rights_boundary": "Abstract sequence knowledge only. No source footage, audio, exact script, artwork, or branding is licensed for reuse; any new video must use original expression.",
  "hook": {
    "description": "先提出观众可感知的问题，再快速预览多个实例；将具体话题和原片文案替换为新主题的认知问题。",
    "duration_seconds": 15.6
  },
  "beats": [
    {
      "beat_id": "hook",
      "order": 1,
      "description": "问题与实例预览；只保留提问到预览的结构。",
      "duration_seconds": 15.6,
      "slot_type": "hook"
    },
    {
      "beat_id": "first-example",
      "order": 2,
      "description": "第一个编号实例：命名、展示动作、解释可感知的结果。",
      "duration_seconds": 6.4,
      "slot_type": "evidence"
    },
    {
      "beat_id": "example-series",
      "order": 3,
      "description": "以相近时长重复编号实例，每段聚焦一个动作和一句解释；新作品的实例与画面必须重新设计。",
      "duration_seconds": 63.0,
      "slot_type": "evidence"
    },
    {
      "beat_id": "principle-close",
      "order": 4,
      "description": "从实例序列回到可迁移的设计原则并结束。",
      "duration_seconds": 8.333333,
      "slot_type": "payoff"
    }
  ],
  "total_duration_seconds": 93.333333,
  "blocked_items": [
    {
      "item": "performance_claim",
      "reason": "来源未提供观看留存或转化数据，不能声称该结构提高效果。"
    }
  ],
  "generation_spec": {
    "prompt": {
      "timing": "问题与快速预览 → 首个短实例 → 连续编号实例 → 原则收束。保留相对节奏，按新主题重写全部实例、文案和时长。"
    },
    "structured_attributes": {
      "beat_count": 4,
      "hook_ratio_band": "mid_15_30",
      "pacing": "hybrid"
    },
    "evidence": [
      {
        "kind": "video",
        "video_ref": "SRC-DY-a37a1d6542469a4bc20707ba",
        "evidence_role": "spec_semantics",
        "start_seconds": 0.0,
        "end_seconds": 15.6,
        "note": "开场提出交互差异并预览；本地源 SHA256 a74cf58646d2dfca0b5ea8e68eb51ad5b684bd351e9ce423713fdadf3987f4ea。"
      },
      {
        "kind": "video",
        "video_ref": "SRC-DY-a37a1d6542469a4bc20707ba",
        "evidence_role": "spec_semantics",
        "start_seconds": 15.6,
        "end_seconds": 22.0,
        "note": "第一个编号实例 SPRING。"
      },
      {
        "kind": "video",
        "video_ref": "SRC-DY-a37a1d6542469a4bc20707ba",
        "evidence_role": "spec_semantics",
        "start_seconds": 22.0,
        "end_seconds": 85.0,
        "note": "连续编号实例，单段通常约 5–6 秒；详见 Brief 场景 2–12。"
      },
      {
        "kind": "video",
        "video_ref": "SRC-DY-a37a1d6542469a4bc20707ba",
        "evidence_role": "spec_semantics",
        "start_seconds": 85.0,
        "end_seconds": 93.333333,
        "note": "末段回到总体原则。"
      }
    ],
    "bindings": [
      {
        "attribute_path": "/structured_attributes/beat_count",
        "evidence_index": 0,
        "grade": "partial"
      },
      {
        "attribute_path": "/structured_attributes/hook_ratio_band",
        "evidence_index": 0,
        "grade": "direct"
      },
      {
        "attribute_path": "/structured_attributes/pacing",
        "evidence_index": 2,
        "grade": "partial"
      }
    ],
    "provenance": {
      "sources": [
        {
          "source_kind": "video",
          "source_record_id": "SRC-DY-a37a1d6542469a4bc20707ba",
          "brief_ref": "[本机绝对路径已隐藏]"
        }
      ]
    },
    "granularity": "sequence"
  },
  "payload_digest": "sha256:4f12a116a3906edd9b209b7e1b533354d8cadb96e0bc063210ca71821112331c"
}
```
