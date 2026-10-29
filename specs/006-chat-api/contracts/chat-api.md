# Contract: Chat API

## Endpoint

`POST /chat`

Request and response media type: `application/json`.

## Request

```json
{
  "message": "Quantos alertas estão disparando?",
  "strategy": "react",
  "reflect": false
}
```

| Field | Type | Required | Default | Rules |
|---|---|---:|---|---|
| `message` | string | Yes | — | Trim outer whitespace; must not be empty. |
| `strategy` | string | No | `react` | Must not be empty; registered values are `react` and `plan_and_execute`. Unknown values return 422. |
| `reflect` | boolean | No | `false` | Strict JSON boolean. Applies the existing reflection wrapper without changing the requested strategy name. |

Extra properties are rejected. The request body must be a JSON object.

## Successful response

Status: `200 OK`

```json
{
  "answer": "Há 3 alertas disparando.",
  "trace": [
    {
      "type": "action",
      "content": "Call list_alerts",
      "tool": "list_alerts",
      "args": {"status": "firing"}
    },
    {
      "type": "observation",
      "content": "{\"items\": [], \"total\": 3}"
    },
    {
      "type": "answer",
      "content": "Há 3 alertas disparando."
    }
  ],
  "metrics": {
    "llm_calls": 2,
    "latency_ms": 140.5
  }
}
```

`trace` event types reuse the existing strategy contract. Action events contain
`tool` and `args`; other event types omit those fields. `llm_calls` is a
non-negative integer and `latency_ms` is a non-negative number.

## Error responses

### 400 Bad Request

Malformed JSON, non-object JSON, missing or invalid fields, blank message,
invalid boolean, or extra fields. Validation responses must omit submitted
values.

```json
{
  "issues": [
    {
      "loc": ["message"],
      "code": "string_too_short",
      "message": "String should have at least 1 character"
    }
  ]
}
```

Each issue contains only `loc`, `code` and `message` derived from Pydantic
validation. It must not include Pydantic `input`, `ctx`, or error URL.

### 422 Unprocessable Entity

```json
{
  "error": {
    "code": "unknown_strategy",
    "message": "The requested strategy is not available."
  }
}
```

### 504 Gateway Timeout

Returned when waiting for strategy execution exceeds 180 seconds.

```json
{
  "error": {
    "code": "strategy_timeout",
    "message": "The strategy execution exceeded the time limit."
  }
}
```

### 500 Internal Server Error

Unexpected operational failure. The server logs diagnostic details; the
response does not expose them.

```json
{
  "error": {
    "code": "internal_error",
    "message": "The request could not be completed."
  }
}
```

### 405 Method Not Allowed

Methods other than `POST` must not execute a strategy. The response follows
Django's method-not-allowed semantics and includes the `Allow: POST` header.

## Behavioral guarantees

- Unknown strategy names are checked after request-shape validation and before
  model or tool construction.
- Invalid input never starts strategy execution.
- Reflection is opt-in and does not change `strategy` accepted values.
- A request exceeding the 180-second execution deadline receives one 504
  response; timeout cancellation is not reported as success.
- No response contains a stack trace, rejected input value, credential, or
  provider-specific error detail.
