# Data Model: What it is

This purpose slice defines conceptual entities only. It does not introduce storage schema, persistence ownership, or runtime state transitions.

## Entities

### Report

- **Definition**: The durable deliverable Baton Flow is for.
- **Purpose**: Accumulates value as AI-assisted work proceeds across sessions.
- **Ownership**: Product-purpose concept in HLD-001. Storage and output mechanics are deferred to later specs.

### Task

- **Definition**: A claimable unit of work whose result contributes to an output path.
- **Purpose**: Provides a manageable unit for runners or humans to work.
- **Ownership**: Mentioned here only as part of HLD-001's purpose model. Lifecycle rules are deferred.

### Runner

- **Definition**: An AI session or human that claims and works a task.
- **Purpose**: Performs work that contributes to durable output.
- **Ownership**: Mentioned here only as part of the purpose model. Session identity and routing are deferred.

### Baton Context

- **Definition**: Durable, readable, steerable context that survives handoffs.
- **Purpose**: Prevents context loss and allows work to continue toward a good report.
- **Ownership**: Mentioned here as the means. Context substrate details are deferred.

### Human Steering

- **Definition**: Human visibility and direction applied while work proceeds.
- **Purpose**: Lets the human see and steer without restarting.
- **Ownership**: Mentioned here as a product need. Human-in-the-loop mechanics are deferred.

## Relationships

- A report is the product deliverable.
- A task contributes work results toward an output path.
- A runner works a task.
- Baton context lets runners continue work across handoffs.
- Human steering guides work without discarding accumulated context.
