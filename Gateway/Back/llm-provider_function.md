# LLM-provider Quick Spec

## 1. Main Parameters

### Common Parameters
- user_input: string, required.
- model: string, optional. If omitted, code fallback is ACTIVE_MODEL.

### Streaming-only Parameter
- smooth: boolean, optional, default true.
  - true: smoother merged chunks.
  - false: finer-grained chunks.

---

## 2. Integration Modes

### Mode A: Streaming (recommended)
Function:
```python
LLM_stream(user_input: str, model: Optional[str] = None, smooth: bool = True) -> Iterator[dict]
```
Use when:
- Need real-time text rendering.
- Need loading interaction with pulse events.

### Mode B: Blocking + metrics
Function:
```python
LLM_with_metrics(user_input: str, model: Optional[str] = None) -> tuple[str, dict]
```
Use when:
- Need full text and performance metrics in one response.

### Mode C: Blocking text only
Function:
```python
LLM(user_input: str, model: Optional[str] = None) -> str
```
Use when:
- Only final text is needed.

---

## 3. Input JSON Format

### Streaming input
```json
{
  "user_input": "请帮我总结这段内容",
  "model": "qwen3.5-flash",
  "smooth": true
}
```

### Blocking input
```json
{
  "user_input": "请帮我总结这段内容",
  "model": "qwen3.5-flash"
}
```

---

## 4. Output JSON Format

## 4.1 Streaming output (event stream)

### pulse event
```json
{
  "type": "pulse",
  "stage": "accepted",
  "elapsed_seconds": 0.0
}
```

```json
{
  "type": "pulse",
  "stage": "first_token",
  "elapsed_seconds": 0.42
}
```

### delta event
```json
{
  "type": "delta",
  "content": "这是分片文本"
}
```

### done event
```json
{
  "type": "done",
  "content": "完整回复文本",
  "metrics": {
    "model": "qwen3.5-flash",
    "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "request_options": {
      "temperature": 0.7
    },
    "first_token_latency_seconds": 0.42,
    "latency_seconds": 1.23,
    "throughput_tokens_per_second": 45.67,
    "prompt_tokens": 120,
    "completion_tokens": 80,
    "total_tokens": 200
  }
}
```

## 4.2 Blocking output (with metrics)
```json
{
  "content": "完整回复文本",
  "metrics": {
    "model": "qwen3.5-flash",
    "first_token_latency_seconds": 0.42,
    "latency_seconds": 1.23,
    "throughput_tokens_per_second": 45.67,
    "prompt_tokens": 120,
    "completion_tokens": 80,
    "total_tokens": 200
  }
}
```

## 4.3 Blocking output (text only)
```json
{
  "content": "完整回复文本"
}
```

---

## 5. Minimal Backend Handling Rule

- On pulse.accepted: start loading animation.
- On pulse.first_token or first delta: stop loading animation and render text.
- On done: finalize response and store metrics.
