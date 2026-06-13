# TestForge — Contrato mínimo de RawRecordedEvent

```json
{
  "schema_version": "0.2.1",
  "event_id": "evt_0001",
  "sequence": 1,
  "timestamp": "ISO-8601 datetime",
  "type": "navigation|click|fill|input|select|check|uncheck|submit",
  "url": "string",
  "page_title": "string",
  "input": {
    "value": "string",
    "value_kind": "literal_observed|test_data_reference|redacted_future",
    "sensitive_data_alert": {
      "possible_sensitive_data_detected": true,
      "detected_categories": ["cpf_pattern"],
      "policy": "alert_only",
      "masking_applied": false
    }
  },
  "target": {
    "tag": "string",
    "role": "string|null",
    "accessible_name": "string|null",
    "label": "string|null",
    "placeholder": "string|null",
    "id": "string|null",
    "name": "string|null",
    "test_id": "string|null",
    "text": "string|null",
    "attributes": {},
    "bounding_box": {},
    "frame_context": {},
    "shadow_context": {},
    "ancestor_summary": [],
    "sibling_summary": []
  },
  "context": {
    "nearby_texts": [],
    "region": "string|null",
    "form_id": "string|null"
  },
  "artifacts": {
    "screenshot": "screenshots/evt_0001.png",
    "dom_snapshot": "dom_snapshots/evt_0001.html",
    "ax_snapshot": "ax_snapshots/evt_0001.json"
  }
}
```
