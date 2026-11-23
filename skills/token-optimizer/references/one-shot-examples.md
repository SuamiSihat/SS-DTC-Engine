# One-Shot Examples Reference

Ready-made input→output examples for 10 domains. Drop these directly into your
prompts to instantly align Claude's output style without lengthy instructions.

One-shot examples work because Claude pattern-matches on the example. One good
example replaces approximately 100 tokens of style description.

---

## How to Use

```
Task: [description]

Example:
Input: [sample input]
Output: [exact output format you want]

Now apply to:
Input: [your actual input]
```

---

## Domain 1 — Code Review

```
Task: Review code and give only critical issues. No compliments.

Example:
Input: def add(a, b): return a+b
Output:
- No type hints — add: def add(a: int | float, b: int | float) -> int | float
- No docstring for public function
- No input validation for edge cases (None, strings)

Now apply to:
Input: [your code]
```

---

## Domain 2 — Email Writing

```
Task: Write a professional email. Subject line included. Under 120 words.

Example:
Input: Ask client why invoice hasn't been paid, it's 2 weeks late
Output:
Subject: Invoice #2847 — Payment Follow-Up

Hi [Name],

I wanted to follow up on Invoice #2847 sent on [date], which was due [due date].
We haven't received payment yet. Could you let me know the expected payment date
or if there's anything needed from our end?

Thank you,
[Your name]

Now write:
Input: [your email situation]
```

---

## Domain 3 — Data Extraction

```
Task: Extract structured data from text. JSON output only.

Example:
Input: "John Smith called on March 3rd about the broken refrigerator at
123 Oak Street. He wants a callback before 5pm."
Output: {"name":"John Smith","date":"March 3","issue":"broken refrigerator",
"address":"123 Oak Street","callback_before":"5pm"}

Now extract from:
Input: [your text]
```

---

## Domain 4 — Content Simplification

```
Task: Rewrite technical content for a general audience. No jargon.

Example:
Input: "The API implements OAuth 2.0 with JWT bearer tokens for stateless
authentication across distributed microservices."
Output: "The system uses a secure login method where each request carries
a digital pass that proves your identity without storing session data."

Now simplify:
Input: [your technical content]
```

---

## Domain 5 — Bullet Point Summary

```
Task: Summarize into exactly 5 bullets. Each bullet max 12 words. Most important first.

Example:
Input: [long article about climate change]
Output:
• Global temperatures have risen 1.1°C above pre-industrial levels
• Arctic ice is melting 3x faster than global average
• 1 billion people face water scarcity by 2025 due to glacial loss
• Renewable energy now cheaper than fossil fuels in 90% of markets
• Net-zero targets require 45% emissions cut by 2030

Now summarize:
Input: [your content]
```

---

## Domain 6 — Social Media Caption

```
Task: Write an Instagram caption. Hook in first line. CTA at end. Max 80 words.

Example:
Input: Launching a new AI course for beginners
Output:
You don't need a coding background to use AI tools. 🤖

We just launched our beginner AI course — 6 modules, real projects,
and a community of 2,000+ learners already inside.

No experience required. Just curiosity.

👇 Link in bio to join free this week.

#AI #LearnAI #OnlineLearning

Now write for:
Input: [your product/topic]
```

---

## Domain 7 — Meeting Notes to Action Items

```
Task: Extract only action items from meeting transcript. Owner + deadline included.

Example:
Input: "Sarah said she'd update the pricing page by Friday. Tom will reach out
to the vendor about delivery timelines next week. We agreed the team would
review the new onboarding flow before the Wednesday call."
Output:
• [ ] Sarah — Update pricing page — Friday
• [ ] Tom — Contact vendor re: delivery timelines — Next week
• [ ] Team — Review new onboarding flow — Before Wednesday call

Now extract from:
Input: [your meeting notes]
```

---

## Domain 8 — Product Description

```
Task: Write an e-commerce product description. Benefits-first. Under 60 words.

Example:
Input: Wireless earbuds, 30hr battery, noise cancelling, IPX5 waterproof
Output:
Lose yourself in music, not the cord. These wireless earbuds deliver 30 hours
of play time with active noise cancellation that blocks out the world.
Sweat-proof and rain-ready with IPX5 waterproofing — built for your busiest days.
$49 | Free shipping

Now write for:
Input: [your product details]
```

---

## Domain 9 — SEO Title + Meta Description

```
Task: Write SEO title (under 60 chars) and meta description (under 155 chars).
Primary keyword must appear in both.

Example:
Input: Blog post about freelancing tips for beginners in Pakistan
Keyword: freelancing for beginners
Output:
Title: Freelancing for Beginners in Pakistan — 10 Proven Tips
Meta: Start your freelancing journey in Pakistan with these 10 beginner tips.
Learn how to find clients, set rates, and earn online fast.

Now write for:
Input: [your page topic and keyword]
```

---

## Domain 10 — Feedback → Actionable Response

```
Task: Convert negative feedback into a specific improvement action. One sentence each.

Example:
Input: "The checkout process is too complicated and I gave up halfway."
Output:
Action: Reduce checkout to 3 steps maximum and add a progress bar showing
current step and estimated time to complete.

Now convert:
Input: [your feedback]
```

---

## Tips for Better One-Shot Examples

1. **Make the example realistic** — a toy example with toy data produces toy outputs
2. **Match the exact format you want** — Claude mirrors structure precisely
3. **One example is usually enough** — two+ examples add tokens without proportional gain
4. **Use your actual domain** — a coding example teaches nothing for email tasks
5. **The example input should be similar in complexity to your real input**
