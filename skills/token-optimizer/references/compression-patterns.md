# Compression Patterns Reference

50+ shorthand patterns organized by category. Use these to compress verbose prompts
into dense, precise instructions that Claude parses faster.

---

## Category 1 — Analysis & Review

| Verbose (avg tokens) | Compressed | Savings |
|---|---|---|
| "Please analyze this and tell me what's happening" (11) | `analyze:` | 85% |
| "Review this code and find any bugs or issues" (13) | `debug:` | 85% |
| "Look at this and tell me how to improve it" (12) | `refine:` | 83% |
| "Do a complete audit of the following" (9) | `audit:` | 78% |
| "Give me a critical evaluation of" (8) | `critique:` | 75% |
| "Compare these two options in detail" (8) | `compare: A vs B` | 50% |
| "What are the pros and cons of" (9) | `pros/cons:` | 67% |
| "Evaluate the risk associated with" (7) | `risk-assess:` | 57% |
| "Perform a SWOT analysis on" (6) | `SWOT:` | 50% |
| "What is missing or incomplete here" (8) | `gaps:` | 88% |

---

## Category 2 — Writing & Content

| Verbose | Compressed |
|---|---|
| "Write a detailed blog post about" | `blog-post:` |
| "Create an email for" | `email:` |
| "Draft a professional message about" | `draft-msg:` |
| "Write a social media caption for" | `caption:` |
| "Generate headline options for" | `headlines(5):` |
| "Create a product description for" | `product-desc:` |
| "Rewrite this to sound more professional" | `rewrite: formal` |
| "Make this shorter without losing meaning" | `compress:` |
| "Translate this to simple language" | `simplify:` |
| "Write in the tone of [X]" | `tone: [X]` |

---

## Category 3 — Code

| Verbose | Compressed |
|---|---|
| "Write a function that" | `fn:` |
| "Debug this and explain the fix" | `debug+explain:` |
| "Refactor this to be cleaner" | `refactor:` |
| "Add error handling to this code" | `add: error-handling` |
| "Convert this from X language to Y" | `convert: X→Y` |
| "Write unit tests for this function" | `tests:` |
| "Optimize this for performance" | `optimize: speed` |
| "Add comments to explain this code" | `add: comments` |
| "Build a complete [X] in [stack]" | `build: [X] ([stack])` |
| "Fix this specific error" | `fix: [error msg]` |

---

## Category 4 — Summarization & Extraction

| Verbose | Compressed |
|---|---|
| "Summarize the key points of" | `summarize:` |
| "Extract the most important information from" | `extract: key-info` |
| "Give me the main takeaways from" | `takeaways:` |
| "List only the action items from" | `action-items:` |
| "What are the key numbers and statistics" | `extract: stats` |
| "Identify all the named entities in" | `extract: entities` |
| "What decisions were made in this meeting" | `extract: decisions` |
| "Give me a one paragraph summary" | `summarize: 1-para` |
| "Give me a one sentence summary" | `summarize: 1-sentence` |
| "Create bullet point notes from" | `notes:` |

---

## Category 5 — Research & Explanation

| Verbose | Compressed |
|---|---|
| "Explain this concept to me simply" | `explain: simple` |
| "Explain as if I'm a complete beginner" | `explain: ELI5` |
| "Give me a technical deep dive on" | `explain: technical` |
| "What is [X] and how does it work" | `what+how: [X]` |
| "Give me background context on" | `context:` |
| "What are the latest developments in" | `latest:` |
| "List the most important things to know about" | `essentials:` |
| "Give me a structured overview of" | `overview:` |
| "What are common mistakes people make with" | `mistakes:` |
| "Step by step how to" | `steps:` |

---

## Category 6 — Generation & Ideation

| Verbose | Compressed |
|---|---|
| "Give me 10 ideas for" | `ideas(10):` |
| "Generate a list of options for" | `options:` |
| "Brainstorm approaches to" | `brainstorm:` |
| "What are creative ways to" | `creative-ways:` |
| "Suggest alternatives to" | `alternatives:` |
| "Create variations of this" | `variations(3):` |
| "What questions should I be asking about" | `questions:` |
| "Give me a template for" | `template:` |
| "Create a checklist for" | `checklist:` |
| "Build a framework for" | `framework:` |

---

## Multi-Task Compression Syntax

When you need multiple outputs from one prompt:

```
[topic/input]:
1. summarize (1 para)
2. key-risks
3. action-items
4. next-steps(3)
```

This bundles 4 separate requests into one structured prompt.

---

## Quantity Modifiers

Add these inline to control output volume:

| Modifier | Meaning |
|---|---|
| `(3)` | Give exactly 3 |
| `max: 5` | No more than 5 |
| `brief` | Short form |
| `detailed` | Full depth |
| `1-liner` | One sentence only |
| `top-3` | Best 3 only |
| `full` | Comprehensive coverage |

---

## Domain Prefixes (Advanced)

For specialized outputs, prefix the domain:

```
legal: review this contract clause
medical: explain this lab result simply
finance: analyze this P&L
marketing: improve this landing page copy
tech: explain this architecture decision
hr: draft a performance review for
```

These prime Claude for domain-appropriate language and standards without lengthy setup.
