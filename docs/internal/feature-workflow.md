# Feature Investigation Workflow

**Every feature in Titan follows this order. No exceptions.**

---

## The Five Steps

### 1. Understand the problem

State the problem in one sentence, from the developer's perspective.

Not: *"We need a Keyboard Builder."*
But: *"The developer thinks in rows, not in builder state."*

If the problem cannot be stated this way, the investigation has not started yet.

---

### 2. Investigate the current Core

Before proposing any solution, study what already exists:

- Is there an API that already covers this? Is it used correctly?
- Is there a documented convention that contradicts the intended usage?
- Is there a model or abstraction that should be used but is not?

Feature #1 (Welcome Recipe) example: `ctx.new_members` returned `list[dict]` while `Sender` already existed in Core. The Recipe revealed a Core inconsistency — not a missing feature.

Feature #2 (Keyboard Builder) example: `InlineKeyboard` already supported the separator pattern. The problem was the documented convention, not the implementation.

---

### 3. Decide whether the problem is real

A problem is real if it exists regardless of any proposed solution.

*"The API is verbose"* is not a real problem until you can say: verbose compared to what, and what cost does that verbosity impose on the developer?

A problem that disappears when the solution is removed is not a problem — it is a preference.

---

### 4. Determine the minimum intervention

If the problem is real, find the smallest intervention that solves it:

| Intervention | Cost | When to use |
|---|---|---|
| Documentation / convention fix | Zero surface cost | When the implementation is correct but poorly explained |
| Small Core improvement | Adds to frozen surface | When there is a genuine inconsistency (existing abstraction not used consistently) |
| New Recipe | Optional, no Core impact | When the pattern is correct but needs a canonical form |
| New feature | Highest cost | When none of the above is sufficient |

Work down this list. Stop at the first intervention that fully solves the problem.

**Do not add a feature to compensate for a problem that a documentation fix would solve.**

---

### 5. Then, and only then, write code

Implementation starts after steps 1–4 are complete and the minimum intervention is chosen.

If the decision is non-trivial, record it as an ADR in `docs/decisions/` before writing code.

---

## The Governing Principle

> Never become attached to the proposed solution. Be attached only to the problem.

A feature proposal is a hypothesis: *"This problem exists, and this solution would fix it."*

Investigation either confirms or refutes that hypothesis. If the hypothesis is wrong — if the problem turns out to be a documentation issue, or a Core inconsistency, or not real at all — the solution is dropped without regret.

Feature #2 is the reference case for this workflow. It was proposed as a new API, investigated thoroughly, and resolved as a documentation correction. No code was added. The outcome was better for it.

---

## Repository Cleanliness Principle

> يجب أن يبدو المستودع كما لو أنه طُوِّر بهذه البنية منذ اليوم الأول، وليس كسلسلة من الترقيعات أو إعادة التنظيمات التاريخية.

الوثائق تصف الحالة الحالية للمشروع، لا تاريخ كل تعديل مرّ به، إلا إذا كانت تلك المعلومة تُضيف قيمة معمارية حقيقية أو تحفظ توافقاً قائماً.

عند اكتمال أي إعادة تنظيم أو إعادة تسمية أو تحسين داخلي، تُزال الآثار التاريخية غير الضرورية حتى يبقى المستودع بسيطاً، متماسكاً، وسهل القراءة للمطور الجديد.

**Why:** الوثائق التي تحمل طبقات من "كان سابقاً..." و"تمت إعادة التسمية من..." تجعل المستودع يبدو كأرشيف تاريخي لا كمشروع حي. المطور الجديد يحتاج أن يفهم ما هو قائم اليوم، لا أن يتتبع سلسلة القرارات للوصول إلى الواقع.

**How to apply:** عند إتمام أي تنظيم أو تسمية أو إعادة هيكلة، راجع كل ملف وثائق يذكر الحالة القديمة واسأل: "هل هذه المعلومة تُفيد قارئاً يريد فهم المشروع اليوم؟ أم أنها سياق تاريخي لجلسة عمل انتهت؟" إذا كانت الإجابة الثانية — احذفها.
