---
card_id: "MOT-DY-BURST-001"
type: "MOT"
status: "active"
version: "1.0.0"
payload_digest: "sha256:ed698085c5b485a6c5ea788c492b94c4604d9b5796fbb37c2f500975d132ace3"
transaction_id: "dy-adp-20260930-1"
source_record_id: "SRC-DY-a37a1d6542469a4bc20707ba"
---
```json
{
  "schema_version": "motion-card/v2",
  "card_id": "MOT-DY-BURST-001",
  "card_type": "MOT",
  "version": "1.0.0",
  "status": "active",
  "source_ids": [
    "SRC-DY-a37a1d6542469a4bc20707ba"
  ],
  "rights_boundary": "Abstract feedback timing and causal sequence only. No source particle artwork, frames, audio, or exact choreography is licensed for reuse.",
  "elements": [
    {
      "role": "primary_feedback",
      "trigger": "click",
      "entry": "scale past resting size",
      "hold": "brief emphasis",
      "exit": "settle to resting size",
      "narrative_purpose": "make the successful action immediately perceptible"
    },
    {
      "role": "secondary_feedback",
      "trigger": "same click, after a short delay",
      "entry": "small particles expand away from action point",
      "hold": "brief visible burst",
      "exit": "fade out and clear the field",
      "narrative_purpose": "acknowledge the action without masking the next explanation"
    }
  ],
  "motion_unresolved": false,
  "reduced_motion_rule": "Keep the immediate state change; suppress the particles and use a short opacity change when reduced motion is requested.",
  "blocked_items": [
    {
      "item": "exact_easing_curve",
      "reason": "The raster video and narration support overshoot and delayed particles, but do not expose a numeric easing curve; spring is a qualitative classification only."
    }
  ],
  "generation_spec": {
    "prompt": {
      "motion": "On a click, show the primary state change immediately. Shortly after, emit a few original secondary marks from the action point; let them expand, pause briefly, fade, and clear before the next beat. Adapt the marks to the new subject."
    },
    "structured_attributes": {
      "motion_level": "medium",
      "entry": "motion.entry.scale_in",
      "hold": "motion.hold.static",
      "exit": "motion.exit.fade_out",
      "easing_family": "spring"
    },
    "evidence": [
      {
        "kind": "video",
        "video_ref": "SRC-DY-a37a1d6542469a4bc20707ba",
        "evidence_role": "spec_semantics",
        "start_seconds": 34.2,
        "end_seconds": 39.8,
        "note": "BURST chapter; narration describes click burst. Frame sequence 34.4/35.2/36.0/37.2s shows emphasis, expansion and fade. Source duration 93.333333s."
      },
      {
        "kind": "video",
        "video_ref": "SRC-DY-a37a1d6542469a4bc20707ba",
        "evidence_role": "spec_semantics",
        "start_seconds": 35.2,
        "end_seconds": 37.2,
        "note": "Temporal samples show secondary marks appear after the primary feedback then fade; on-screen annotation states roughly 0.1s delay and scale overshoot."
      }
    ],
    "bindings": [
      {
        "attribute_path": "/structured_attributes/motion_level",
        "evidence_index": 0,
        "grade": "partial"
      },
      {
        "attribute_path": "/structured_attributes/entry",
        "evidence_index": 0,
        "grade": "partial"
      },
      {
        "attribute_path": "/structured_attributes/hold",
        "evidence_index": 1,
        "grade": "partial"
      },
      {
        "attribute_path": "/structured_attributes/exit",
        "evidence_index": 1,
        "grade": "direct"
      },
      {
        "attribute_path": "/structured_attributes/easing_family",
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
    "granularity": "primitive"
  },
  "payload_digest": "sha256:ed698085c5b485a6c5ea788c492b94c4604d9b5796fbb37c2f500975d132ace3"
}
```
