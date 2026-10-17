---
name: coding-style
description: Apply maintainable coding and test style when implementing changes in an existing codebase.
---

# Coding style

- Follow the repository's existing formatting, naming, module layout, and public API conventions. Check nearby code before introducing a new pattern.
- Keep each change focused on the requested behavior. Prefer simple, readable code over clever abstractions; add a helper only when it removes meaningful duplication or clarifies intent.
- Use names that explain purpose. Keep functions small enough that their control flow is clear, and handle errors explicitly where callers need to distinguish them.
- Preserve compatibility unless the approved design requires a change. Avoid unrelated cleanup, formatting churn, new dependencies, and speculative features.
- Write tests around observable behavior and relevant failure cases. Make tests deterministic and independent. Never weaken an assertion, skip a test, or change expected behavior solely to hide a failure.
- Comment on non-obvious intent or constraints; do not narrate obvious code. Update nearby documentation when behavior or a public interface changes.
- Before finishing, inspect the diff for accidental changes and confirm the implemented behavior still matches the requirements and design.
