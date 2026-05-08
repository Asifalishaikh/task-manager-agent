Agents
1. Task Manager Agent

Type: Orchestrator
SDK: OpenAI Agent SDK

Role:
Acts as the primary interface between the user and the system.

Responsibilities:

Receive and interpret user input
Determine user intent
Route tasks to appropriate downstream agents
Aggregate and return responses to the user

Example Input:

"Add reminder for meetup with friend at 8pm"

Behavior:

Identifies this as a scheduling/reminder task
Delegates execution to the Appointment Booking Agent
2. Appointment Booking Agent

Type: Specialized Agent
SDK: OpenAI Agent SDK

Role:
Handles all scheduling and booking-related tasks.

Responsibilities:

Extract structured information from user input:
Event title
Time
Participants (if any)
Record booking details into a storage system (e.g., Google Sheets)
Trigger notification workflows

Output:
Structured booking data and confirmation status

Services
1. Notification API

Framework: FastAPI

Role:
Responsible for sending reminders and notifications to users.

Responsibilities:

Accept notification requests from agents
Deliver reminders via configured channels

Future Extensions:

Email notifications
SMS / WhatsApp integration
Push notifications
2. Storage (Google Sheets)

Role:
Persist structured booking data.

Responsibilities:

Store event details captured by the Appointment Booking Agent
Provide a simple, human-readable log of scheduled tasks

Future Extensions:

Replace or complement with a database (PostgreSQL, MongoDB)
Data Flow

User submits a request:

Add reminder for meetup with friend at 8pm
Task Manager Agent:
Parses input
Detects intent (reminder/scheduling)
Routes to Appointment Booking Agent
Appointment Booking Agent:
Extracts structured data
Stores data in Google Sheets
Calls Notification API
Notification API:
Schedules or sends reminder
System returns confirmation to user
Communication Model
Task Manager Agent ↔ Appointment Booking Agent
Appointment Booking Agent → Storage Service
Appointment Booking Agent → Notification API

Communication is currently synchronous but can be extended to event-driven or asynchronous models.

Design Principles
Separation of Concerns: Each agent has a clearly defined responsibility
Modularity: Agents and services can be independently developed and replaced
Extensibility: New agents can be added without changing core orchestration logic
Interoperability: Designed to integrate with external APIs and SDKs

Creator Workflow & Engineering Standards
1. Always Verify What You Are Doing: Never trust output blindly. Instrument all changes and use tools (tests, linters, dry-runs) to verify work. Implement feedback loops to check results.
2. Plan Mode First: Always research and strategize before execution. Verify the plan before making code changes.
3. Test-Driven Development (TDD): Follow TDD for all development. Write tests first, then implement logic.
4. No JSON Formats: Avoid JSON for data exchange and configuration where possible, preferring more readable or idiomatic formats as per project constraints.
5. Kubernetes (K8s) Perspective: Keep K8s deployment in mind from the start. Design for scalability, statelessness, and containerization.
6. Self-Evolving Documentation: Update GEMINI.md or CLAUDE.md when mistakes are made to prevent recurrence.

Future Enhancements
Introduce LLM-based intent detection and entity extraction
Add memory layer for context-aware interactions
Implement multi-agent collaboration patterns
Introduce task queues for asynchronous processing
Expand agent ecosystem (e.g., Travel Agent, Personal Assistant)

