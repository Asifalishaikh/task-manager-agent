# Agents

## Available Skills

This project uses the [skills](https://github.com/anthropics/skills) system. Installed skills are in `.agents/skills/`.

### mcp-builder
- **Location:** `.agents/skills/mcp-builder/`
- **Use case:** Guide for building high-quality MCP servers (Python FastMCP or TypeScript MCP SDK)
- **When to use:** When building MCP servers to integrate external APIs/services
- **How to use:** Load `SKILL.md` from the skill directory when starting MCP server work

---

## 1. Task Manager Agent

- **Type:** Orchestrator
- **SDK:** OpenAI Agent SDK

### Role
Acts as the primary interface between the user and the system.

### Responsibilities
- Receive and interpret user input
- Determine user intent
- Route tasks to appropriate downstream agents
- Aggregate and return responses to the user
- **Verify routing decisions before delegating** (confirm downstream agent is correct for the task)
- **Check task completion status** and confirm results before reporting to user

### Example Input
```
"Add reminder for meetup with friend at 8pm"
```

### Behavior
1. Identifies this as a scheduling/reminder task
2. **Verifies intent detection** (is this really scheduling or something else?)
3. Delegates execution to the Appointment Booking Agent
4. **Verifies delegation result** (confirms the downstream agent accepted the task)
5. Returns confirmation to user

---

## 2. Appointment Booking Agent

- **Type:** Specialized Agent
- **SDK:** OpenAI Agent SDK

### Role
Handles all scheduling and booking-related tasks.

### Responsibilities
- Extract structured information from user input:
  - Event title
  - Time
  - Participants (if any)
- Record booking details into a storage system (e.g., Google Sheets)
- Trigger notification workflows
- **Verify extracted data** (confirm title, time, participants are valid before storing)
- **Verify storage operation** (confirm data was persisted successfully)
- **Verify notification delivery** (confirm notification was sent or scheduled)

### Output
- Structured booking data and confirmation status
- **Verification evidence** (proof of storage + notification)

---

## Services

### 1. Notification API

- **Framework:** FastAPI

#### Role
Responsible for sending reminders and notifications to users.

#### Responsibilities
- Accept notification requests from agents
- Deliver reminders via configured channels
- **Verify delivery status** and report back to calling agent

#### Future Extensions
- Email notifications
- SMS / WhatsApp integration
- Push notifications

### 2. Storage (Google Sheets)

#### Role
Persist structured booking data.

#### Responsibilities
- Store event details captured by the Appointment Booking Agent
- Provide a simple, human-readable log of scheduled tasks
- **Confirm write operations** with success/error response

#### Future Extensions
- Replace or complement with a database (PostgreSQL, MongoDB)

---

## Data Flow

### User submits a request:
```
Add reminder for meetup with friend at 8pm
```

### Step-by-step with verification checkpoints:

**1. Task Manager Agent:**
- Parses input
- Detects intent (reminder/scheduling)
- **🔍 VERIFY:** Is the intent correctly identified? (Run secondary check)
- Routes to Appointment Booking Agent
- **🔍 VERIFY:** Did the downstream agent accept the task? (Check response)

**2. Appointment Booking Agent:**
- Extracts structured data
- **🔍 VERIFY:** Are all required fields present and valid? (Title, time, participants)
- Stores data in Google Sheets
- **🔍 VERIFY:** Did storage succeed? (Check write confirmation)
- Calls Notification API
- **🔍 VERIFY:** Was notification scheduled/delivered? (Check API response)

**3. Notification API:**
- Schedules or sends reminder
- **🔍 VERIFY:** Confirm delivery or scheduling status

**4. System returns confirmation to user** with all verification evidence

---

## Communication Model

- Task Manager Agent ↔ Appointment Booking Agent (bidirectional)
- Appointment Booking Agent → Storage Service (with response verification)
- Appointment Booking Agent → Notification API (with response verification)

### Current state
Communication is synchronous but can be extended to event-driven or asynchronous models.

### Verification requirement
Every communication must be confirmed. No fire-and-forget calls.

---

## Design Principles

| Principle | Description |
|-----------|-------------|
| **Separation of Concerns** | Each agent has a clearly defined responsibility |
| **Modularity** | Agents and services can be independently developed and replaced |
| **Extensibility** | New agents can be added without changing core orchestration logic |
| **Interoperability** | Designed to integrate with external APIs and SDKs |
| **Verify by Default** | Every action must have a corresponding verification checkpoint |
| **Feedback Loops** | Always instrument changes to measure outcomes and catch errors |

---

## Creator Workflow & Engineering Standards

*(Adapted from [The Creator's Workflow: Claude Code Best Practices](https://agentfactory.panaversity.org/docs/General-Agents-Foundations/general-agents/creator-workflow) — Boris Cherny, Anthropic)*

### 1. Always Verify What You Are Doing
Never trust output blindly. Instrument all changes. **Give every agent a way to verify its own work.** Quality comes from feedback loops, not hope.

**Practical implementation:**
- Every agent task must end with a verification step
- Use MCP tools, hooks, or subagents to auto-verify outputs
- Run verification commands (`build`, `test`, `typecheck`) after every change
- If verification fails, **stop, re-plan, and fix** before proceeding
- **Verification 2-3x's the quality of the final result** (per Boris Cherny)

### 2. Context Window Awareness
Claude's context window fills up fast, and performance degrades as it fills.

**How we manage context:**
- Use parallel sessions for different workstreams (each session = isolated context window)
- Run `clear` between unrelated tasks to reset context
- Use subagents for investigation (they explore in separate context, report summaries back)
- Run a session-end review skill before closing to capture insights while context is fresh
- When things go wrong multiple times on the same issue, `clear` and rewrite the prompt

### 3. Parallel Sessions
Running multiple isolated sessions is the single biggest productivity unlock.

- One session per major feature or workstream
- Use **git branches** for isolating work (e.g., `feature/mcp-server`, `feature/db-persistence`)
  - Worktrees add complexity; branches keep everything in one working tree
- Name sessions descriptively using `/rename` so you can resume them later
- Start with 3 sessions before scaling up

### 4. Plan Mode First (Always)
For every non-trivial task: research and strategize before execution.

1. Start with a clear goal
2. Enter Plan Mode
3. Discuss and refine until the plan makes sense
4. Switch to execution
5. If things go sideways, switch back to Plan Mode and re-plan
6. **Do not push through a confused execution**

### 5. Claude-Reviews-Claude Pattern
Use separate sessions for writing and reviewing.

- **Session A (Writer):** Create the implementation plan
- **Session B (Reviewer):** Review with fresh eyes (staff engineer persona)
- **Session A:** Address feedback, iterate

**Why it works:** Fresh context catches blind spots. Different "persona" surfaces different concerns. Two-pass verification before any code is written.

### 6. Self-Evolving Documentation (CLAUDE.md / AGENTS.md)
Document mistakes immediately so they never repeat.

**The magic phrase:** *"Update your CLAUDE.md so you don't make that mistake again."*

- When Claude makes a mistake, correct it and immediately update this file
- Claude is surprisingly good at writing rules for itself
- Over weeks, this file becomes institutional memory that prevents entire categories of mistakes
- **Prune ruthlessly:** If Claude already does something correctly, remove the rule (don't over-specify)

### 7. Skills for Workflow Automation
*"If you do something more than once a day, turn it into a skill."* — Boris Cherny

**Must-have skills for this project:**
- `/verify` — Run comprehensive verification (tests, lint, build) after every change
- `/session-review` — Summarize session decisions, follow-ups, and insights worth capturing
- `/commit` — Pre-compute git status, create clean, verified commits
- `/context-dump` — Sync relevant context (git log, changes, issues) into one place

### 8. Session Management

| Action | When to Use |
|--------|-------------|
| `Esc` | Stop Claude mid-action (context is preserved) |
| `Esc + Esc` or `/rewind` | Restore previous conversation and code state |
| `/clear` | Reset context between unrelated tasks |
| `/rename` | Give sessions descriptive names (`"oauth-migration"`) |
| `--continue` / `--resume` | Resume conversations later |

**When to abandon:** 10-20% of sessions hit unexpected scenarios. This is normal. Starting fresh is often faster than recovering a confused session.

### 9. Verification Infrastructure
This is the **most important** insight from the Creator's Workflow:

> *"Probably the most important thing to get great results out of Claude Code: give Claude a way to verify its work. If Claude has that feedback loop, it will 2-3x the quality of the final result."*
> — Boris Cherny

**Implementation in this project:**
- Every agent must have verification tools available (MCP, subagents, scripts)
- After every file write or edit, run automated checks (tests, linters, typecheck)
- Use PostToolUse hooks to auto-format files after writing
- **Don't trust AI output — instrument it**

### 10. Test-Driven Development (TDD)
Follow TDD for all development. Write tests first, then implement logic.

- Every new feature starts with a failing test
- Verification = TDD (tests are your verification feedback loop)
- Run tests after every change

### 11. No JSON Formats
Avoid JSON for data exchange and configuration where possible, preferring more readable or idiomatic formats.

### 12. Kubernetes (K8s) Perspective
Keep K8s deployment in mind from the start. Design for scalability, statelessness, and containerization.

- All agents should be stateless
- Use environment variables for configuration
- Design for horizontal scaling from day one

### 13. Prompting Workflow
- **Challenge prompts:** "Grill me on these changes" / "Poke holes in this plan"
- **Escape mediocre solutions:** "Knowing everything you know now, scrap this and create the elegant solution"
- **Reduce ambiguity:** Write detailed briefs with constraints, audience, and success criteria
- **Give Claude the problem, not the solution** — it often finds better approaches

### 14. Permissions & Safety
Use `/permissions` to pre-allow safe commands. **Never use `--dangerously-skip-permissions`.**

- Pre-allow: `bun run build:*`, `bun run test:*`, `bun run typecheck:*`
- Share permissions in `.claude/settings.json` with the team
- Maintain safety boundaries while enabling efficient workflows

---

## Common Failure Patterns to Avoid

| Pattern | Symptom | Fix |
|---------|---------|-----|
| **Kitchen sink session** | Started with one task, asked unrelated questions, context cluttered | `clear` between unrelated tasks |
| **Correction spiral** | Corrected Claude twice, still wrong, correcting again | After 2 failed corrections, `clear` and rewrite the initial prompt |
| **Over-specified rules** | Important rules get lost in noise | Prune ruthlessly. If Claude already does it correctly, delete the rule |
| **Trust-then-verify gap** | Plausible-looking output that doesn't handle edge cases | Always provide verification methods |
| **Infinite exploration** | "Investigate" without scope; context fills with reads | Scope investigations narrowly or use subagents |

---

## Future Enhancements

- Introduce LLM-based intent detection and entity extraction
- Add memory layer for context-aware interactions
- Implement multi-agent collaboration patterns
- Introduce task queues for asynchronous processing
- Expand agent ecosystem (e.g., Travel Agent, Personal Assistant)
- Build session-end review skill for capturing work summaries
- Implement Claude-Reviews-Claude pattern for plan validation
- Create portable skill portfolio shared across projects

