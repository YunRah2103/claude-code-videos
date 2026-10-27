---
name: ponytail
description: Reduce code output by optimising it. Use when the user asks for "ponytail" or "ponytail full", or wants shorter, leaner code.
---

# Ponytail

Goal: produce the least code that fully does the job, without losing correctness or readability.

When this skill is active:

1. **Write the minimum.** Solve the stated problem and nothing more. No speculative features, no extra abstractions, no wrapper functions used once.
2. **Cut duplication.** If a block repeats, extract it once or use a loop, map, or data table.
3. **Prefer built-ins and existing code.** Check what the repo already has before writing a helper. Use the language's standard library or the project's dependencies.
4. **Flatten.** Remove redundant variables, nested ifs that can be early returns, and intermediate values used only once.
5. **Keep it readable.** Match the surrounding code's naming, comment density, and idiom. Shorter must not mean cryptic.
6. **Don't change behaviour.** Run the repo's existing checks (lint, typecheck, tests) before and after. If there are none, verify by reading the diff.
7. **Report the reduction.** After optimising, state the lines or files changed and what was removed or merged, in one short summary.

When the user asks for "ponytail full", apply all of the steps above to the code in scope. Otherwise apply them to the code you are about to write.
