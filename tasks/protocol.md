# Task Dispatcher Protocol

## Directory Structure

- `queue/` - Coordinator drops new tasks here
- `active/` - Worker moves task here while working
- `done/` - Completed tasks with results

## Task Format (JSON)

```json
{
  "id": "001",
  "description": "What to do",
  "type": "code|research|review",
  "context": "Relevant information",
  "created_by": "coordinator"
}
```

## Completion Format

Worker adds these fields before moving to `done/`:

```json
{
  "status": "done|failed",
  "result": "What was accomplished or found",
  "completed_by": "worker"
}
```

## Protocol

1. Coordinator writes task file to `queue/`
2. Worker polls `queue/`, picks up oldest task
3. Worker moves task to `active/`
4. Worker does the work
5. Worker adds result fields, moves to `done/`
6. Coordinator reads result from `done/`
