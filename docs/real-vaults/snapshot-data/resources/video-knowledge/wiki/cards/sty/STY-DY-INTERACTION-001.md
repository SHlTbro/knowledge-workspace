---
card_id: "STY-DY-INTERACTION-001"
type: "STY"
status: "active"
version: "1.0.0"
payload_digest: "sha256:07f9b70b4f6e7f7175a9bb55f7a964a941f8a542f5420b53513f3fd3bebcd4b3"
transaction_id: "dy-adp-20260930-1"
source_record_id: "SRC-DY-a37a1d6542469a4bc20707ba"
---
```json
{
  "schema_version": "style-card/v2",
  "card_id": "STY-DY-INTERACTION-001",
  "card_type": "STY",
  "version": "1.0.0",
  "status": "active",
  "source_ids": [
    "SRC-DY-a37a1d6542469a4bc20707ba"
  ],
  "rights_boundary": "Layout and color observations are research metadata, not a license to reproduce the source design or media. New render must change palette and create original shapes, text, and UI.",
  "color_tokens": [
    {
      "role": "neutral_surround",
      "hex": "#e6ebf1",
      "frame_sha256": "c01ae7e58afe308dd12eb5bf2b673e993c30be1a772e655dbe7154d75f21f31d"
    },
    {
      "role": "demo_canvas",
      "hex": "#ffffff",
      "frame_sha256": "c01ae7e58afe308dd12eb5bf2b673e993c30be1a772e655dbe7154d75f21f31d"
    },
    {
      "role": "local_accent_sample",
      "hex": "#6fd6bb",
      "frame_sha256": "c01ae7e58afe308dd12eb5bf2b673e993c30be1a772e655dbe7154d75f21f31d"
    }
  ],
  "typography": {
    "category": "bold sans-serif headings with smaller explanatory labels",
    "font_family": "unknown; no source font file or metadata"
  },
  "layout": {
    "pattern": "two-zone demonstration and explanation",
    "normalized_regions": {
      "demo": [
        0.09,
        0.25,
        0.4,
        0.49
      ],
      "explanation": [
        0.52,
        0.16,
        0.38,
        0.44
      ]
    },
    "regions_are_approximate": true
  },
  "prohibited_copy": [
    "Do not reuse source video frames, UI artwork, branding, watermark, or exact on-screen copy.",
    "Source license is unproven; redraw all shapes and text for the new topic."
  ],
  "blocked_items": [
    {
      "item": "exact_font_and_assets",
      "reason": "No source design files or separate license evidence; font and artwork cannot be identified or reused."
    }
  ],
  "generation_spec": {
    "prompt": {
      "visual": "A light neutral field separates a concise explanation from an original animated demonstration. Keep one clear accent and generous space; redraw all content for the new subject."
    },
    "structured_attributes": {
      "palette": [
        "#e6ebf1",
        "#ffffff",
        "#6fd6bb"
      ],
      "composition": "grid_split",
      "lighting": "high_key",
      "visual_density": 0.35
    },
    "evidence": [
      {
        "kind": "video",
        "video_ref": "SRC-DY-a37a1d6542469a4bc20707ba",
        "evidence_role": "spec_semantics",
        "start_seconds": 46.3,
        "end_seconds": 52.4,
        "note": "Frame at 48.0s, SHA256 c01ae7e58afe308dd12eb5bf2b673e993c30be1a772e655dbe7154d75f21f31d; sampled neutral/white/accent values and two-zone layout."
      },
      {
        "kind": "video",
        "video_ref": "SRC-DY-a37a1d6542469a4bc20707ba",
        "evidence_role": "spec_semantics",
        "start_seconds": 68.9,
        "end_seconds": 74.4,
        "note": "Frame at 70.5s, SHA256 c99eb296b8c979b5dd83107ee805689e505972a4ad992506f8fd636184e4c306; repeated explanation/demo arrangement."
      },
      {
        "kind": "video",
        "video_ref": "SRC-DY-a37a1d6542469a4bc20707ba",
        "evidence_role": "spec_semantics",
        "start_seconds": 79.6,
        "end_seconds": 85.0,
        "note": "Frame at 81.5s, SHA256 ec6f04486d52eee3cba33fb677217e5c88777b1eb7764438295975fbfdec25e8; repeated light visual field."
      }
    ],
    "bindings": [
      {
        "attribute_path": "/structured_attributes/palette/0",
        "evidence_index": 0,
        "grade": "partial"
      },
      {
        "attribute_path": "/structured_attributes/palette/1",
        "evidence_index": 0,
        "grade": "direct"
      },
      {
        "attribute_path": "/structured_attributes/palette/2",
        "evidence_index": 0,
        "grade": "partial"
      },
      {
        "attribute_path": "/structured_attributes/composition",
        "evidence_index": 0,
        "grade": "partial"
      },
      {
        "attribute_path": "/structured_attributes/lighting",
        "evidence_index": 2,
        "grade": "partial"
      },
      {
        "attribute_path": "/structured_attributes/visual_density",
        "evidence_index": 1,
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
    "granularity": "style_pattern"
  },
  "payload_digest": "sha256:07f9b70b4f6e7f7175a9bb55f7a964a941f8a542f5420b53513f3fd3bebcd4b3"
}
```
