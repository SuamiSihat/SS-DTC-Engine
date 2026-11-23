# Context Management & Conversation Pruning

In long conversations and multi-turn applications, context management is where most
token waste happens. This guide covers how to keep sessions lean without losing quality.

---

## The Problem

Claude has no memory between API calls. Every message in history is re-sent every time.
A 20-message conversation can carry 8,000–15,000 tokens of history — most of it
irrelevant to the current task.

**Cost example:**
- Unmanaged 20-message session: ~12,000 input tokens per message
- Optimized with context pruning: ~800 input tokens per message
- Savings: **93%**

---

## Technique 1 — The State Summary Method

Instead of sending full chat history, replace it with a compact state summary.

**Template:**
```xml
<context_summary>
  goal: [what user is trying to accomplish]
  completed: [what has already been done]
  current_task: [what we're working on right now]
  key_decisions: [any choices already made that affect future work]
  constraints: [rules that apply to all remaining work]
  stack_or_format: [technical context if relevant]
</context_summary>
```

**Before (full history — ~3,000 tokens):**
```
User: I want to build a website for my restaurant
Claude: Great! I can help with that. What kind of restaurant is it?
User: Pakistani food, called Zam Zam Restaurant in Sargodha
Claude: That's wonderful. Let's start with the homepage...
[16 more messages]
```

**After (state summary — ~80 tokens):**
```xml
<context_summary>
  goal: build restaurant website for Zam Zam Restaurant (Pakistani food, Sargodha)
  completed: homepage, menu page, about page
  current_task: contact page with WhatsApp order form
  constraints: mobile-first, no backend, WhatsApp integration, HTML/CSS/JS only
  key_decisions: dark theme, Urdu + English bilingual, one-page checkout
</context_summary>
Continue with current_task only.
```

---

## Technique 2 — Rolling Compression

For ongoing conversations, compress the history after every 5–7 exchanges.

**Trigger:** When history exceeds 2,000 tokens

**Compression prompt (send as system message):**
```
Compress the conversation so far into a context_summary block following this schema:
{goal, completed, current_task, key_decisions, constraints}
Max 100 words total. Preserve all decisions and constraints. Discard pleasantries
and exploratory discussion.
```

Replace the old history with the compressed summary. Continue from there.

---

## Technique 3 — Stateless Message Design

Design each message to be complete without relying on conversational context.

**Stateful (bad — requires history):**
```
Now apply the same approach to this new dataset.
```

**Stateless (good — self-contained):**
```
Apply k-means clustering (k=3) to the following dataset. Return: cluster labels,
centroid coordinates, inertia score. Format: JSON.
Dataset: [data]
```

Each message should be independently executable. This also makes debugging easier
and allows conversation history to be stripped more aggressively.

---

## Technique 4 — Role Pinning

Re-state the role/persona at the top of each request in long sessions instead of
relying on it being remembered from early system prompt.

**Instead of relying on system prompt:**
```
[As the Python code assistant]: Refactor this function for readability.
```

Short role re-pins cost 5–10 tokens and prevent role drift in long sessions.

---

## Technique 5 — Reference File Injection

Instead of including large reference content in every message, inject it only when needed.

**Pattern:**
```
[REFERENCE — only applies to this message]:
[relevant content block]

Task using above reference: [specific task]
```

After the task is done, the reference is not re-sent. This is especially useful for:
- Product documentation
- Code standards / style guides
- Business rules
- Example datasets

---

## Technique 6 — Checkpoint Commits

At logical milestones in a long task, "commit" the state and start a fresh conversation
with just the committed state. Treat it like a git commit.

**Checkpoint message template:**
```
CHECKPOINT: [task name] — [date/session ID]

Completed work:
[summarized output or file references]

Remaining tasks:
1. [next task]
2. [task after that]

Active constraints: [list]
Next message: [what to send to continue]
```

Save this checkpoint externally. Start a new Claude session with only the checkpoint.

---

## Technique 7 — Explicit Context Scope

Tell Claude exactly what context is relevant. This prevents it from drawing on
earlier irrelevant parts of history.

```
For this task, relevant context is ONLY:
- [specific fact 1]
- [specific fact 2]
Ignore all other prior discussion.
```

This is especially useful when changing topics mid-conversation.

---

## Quick Reference — When to Apply Each Technique

| Situation | Technique |
|---|---|
| Starting a new long project | State Summary Method (set up from message 1) |
| Conversation getting expensive | Rolling Compression |
| Building a stateless API app | Stateless Message Design |
| Long creative or coding session | Role Pinning + Checkpoints |
| Need to inject large docs | Reference File Injection |
| Topic shift in conversation | Explicit Context Scope |

---

## Token Cost of Common History Sizes

| History Length | Approx Input Tokens Per Call |
|---|---|
| 5 messages | ~1,500 |
| 10 messages | ~3,500 |
| 20 messages | ~9,000 |
| 40 messages | ~22,000 |
| State summary only | ~60–120 |

**Takeaway:** A state summary replaces 20 messages of history for 1–2% of the cost.
