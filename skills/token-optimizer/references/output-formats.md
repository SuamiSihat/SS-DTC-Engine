# Output Format Templates

Explicit format instructions eliminate response bloat. These templates are ready to
append to any prompt. Choose the format that matches your use case.

---

## Format 1 — Bullet Points (General)

```
Format: bullet points
Rules: max 6 bullets, each bullet max 15 words, no sub-bullets unless critical
```

**When to use:** Quick overviews, feature lists, key takeaways, comparison highlights

---

## Format 2 — Numbered Steps

```
Format: numbered steps
Rules: action verb starts each step, one action per step, no explanatory paragraphs
```

**When to use:** Tutorials, processes, how-to guides, setup instructions

---

## Format 3 — Table

```
Format: markdown table
Columns: [col1] | [col2] | [col3]
Rules: no rows outside table, no intro paragraph, no summary after table
```

**When to use:** Comparisons, data, pricing, feature matrices, schedules

---

## Format 4 — JSON

```
Format: valid JSON only
Schema: { "key": "value" }
Rules: no markdown fences, no explanation text, parseable JSON only
```

**When to use:** API integrations, data extraction, structured output for applications

---

## Format 5 — Code Block

```
Format: code block only ([language])
Rules: no explanation unless I ask "explain:", production-ready, include comments
for non-obvious logic only
```

**When to use:** Code generation, scripts, functions, configuration files

---

## Format 6 — Structured Sections

```
Format: sections with bold headers
Sections: [Section 1] | [Section 2] | [Section 3]
Rules: each section max 3 sentences, no section longer than others by more than 50%
```

**When to use:** Reports, analyses, structured documents, multi-part answers

---

## Format 7 — One-Liner

```
Format: single sentence only
Rules: no preamble, no explanation, answer in one sentence maximum
```

**When to use:** Quick facts, definitions, yes/no questions with brief justification

---

## Format 8 — Two-Column Comparison

```
Format: two-column comparison (Option A vs Option B)
Structure:
| Aspect | Option A | Option B |
Rules: max 8 rows, include a "Winner" row at the bottom
```

**When to use:** Decision-making, product comparisons, approach tradeoffs

---

## Format 9 — Executive Summary

```
Format: executive summary
Structure:
- Bottom line: [1 sentence]
- Key points: [3 bullets max]
- Recommendation: [1 sentence]
Rules: total under 100 words, no background/context section
```

**When to use:** Business decisions, reports for non-technical audiences, briefings

---

## Format 10 — Q&A Pairs

```
Format: Q&A pairs
Structure: Q: [question] / A: [answer, max 2 sentences]
Rules: no narrative between pairs, cover [N] most important questions
```

**When to use:** FAQ generation, knowledge base content, interview prep

---

## Universal Anti-Filler Block

Add this to any prompt to eliminate all padding:

```
NO:
- Intro sentences ("Sure!", "Great question!", "Of course!")
- Restatement of my prompt
- Conclusion paragraphs ("I hope this helps!")
- Unnecessary qualifiers ("It's worth noting that...")
- Hedging unless factually required ("This may vary but generally...")
Start your response with the first word of actual content.
```

---

## Format by Output Length

| Goal | Instruction |
|---|---|
| Ultra-short | `max: 50 words` |
| Short | `max: 100 words` |
| Medium | `max: 300 words` |
| Long | `max: 600 words` |
| Comprehensive | `min: 800 words, cover fully` |
| Exact | `exactly [N] words` |

---

## Combining Format + Length + Restriction

**Most powerful formula:**
```
Format: [type] | Length: [constraint] | Rules: no filler, no rephrasing prompt,
start with [first word/section name]
```

**Example:**
```
Format: numbered steps | Length: max 8 steps | Rules: no intro, no filler,
each step starts with a verb, start with "1."
```
