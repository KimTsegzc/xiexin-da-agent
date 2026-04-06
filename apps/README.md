# apps Layer

`apps` is the thin entrypoint layer.

- `apps/api/server.py`: HTTP transport and route orchestration.
- `Backend/*`: runtime logic, model provider, settings, skills, and contracts.

Design rule:

- Keep `apps` lightweight (adapter/entrypoint only).
- Keep business/domain logic in `Backend`.
