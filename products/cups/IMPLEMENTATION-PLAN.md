# CUPS — Implementation Plan

> هذه ليست وثيقة فلسفية.
> هي ترتيب البناء.
>
> كل Phase يُنتج شيئاً يعمل فعلاً — لا مجرد كود جاهز للـ Phase التالية.

---

## المبدأ الذي يحكم هذا الترتيب

**أبنِ أضيق شيء يعمل نهاية لنهاية أولاً.**

Phase 1 يجب أن تُنتج نظاماً حقيقياً — حتى لو كان Starter فقط، بلا دفع، بلا Atlas.
كل Phase بعدها توسّع على شيء يعمل، لا تُكمل شيئاً مكسوراً.

---

## Phase 1 — الهيكل الأساسي

**الهدف:** نظام يعرف من أنت وما تملك.

### ما يُبنى

**CUPS Core (Python Service):**
- `Account` — ينشأ عند أول `/start`
- `Project` — يُسجَّل عبر `/addbot`، يُعطي `project_id`
- `Subscription` — Starter فقط، تلقائية، بلا دفع
- `Entitlement Resolution` — يحوّل Subscription → Resolved Entitlements
- `Runtime API` — endpoint واحد:
  ```
  POST /entitlements/check
  { account_id, project_id, entitlement }
  → { granted: true/false, value: ... }
  ```

**CUPS Bot (Telegram Bot):**
- `/start` — ينشئ Account أو يسترجعه
- `/addbot` — يسجّل Project ويُعطي `project_id`
- `/plan` — يعرض الخطة الحالية والـ Entitlements

### ما لا يُبنى في هذه المرحلة
- لا دفع
- لا Trial
- لا Atlas أو أي Entitlement مدفوع فعلي
- لا فريق

### كيف تعرف أنها انتهت
```
مطور يفتح CUPS Bot
       ↓ /addbot
       ↓ يحصل على project_id
       ↓ يضعه في كوده
       ↓ يستدعي /entitlements/check
       ↓ يحصل على { granted: false } لأي Entitlement مدفوع
       ↓ يحصل على { granted: true } لـ Entitlements الـ Starter
```

---

## Phase 2 — titan-extension-cups

**الهدف:** أي مطور Titan يستطيع ربط بوته بـ CUPS في 5 دقائق.

### ما يُبنى

**`titan-extension-cups` (Python Package):**
```python
cups = CUPSGuard(api_key="...", project_id="abc123")
bot.middleware(cups.as_middleware())

# الاستخدام
@bot.command("export")
async def export_data(ctx):
    if not await cups.require(ctx, entitlement="data_export"):
        return
    # ... المنطق الفعلي
```

- `CUPSGuard.as_middleware()` — يُشغَّل على كل update، يُضيف `ctx.entitlements`
- `cups.require(ctx, entitlement)` — يُوقف التنفيذ ويُبلّغ المستخدم إذا لم يملك الحق
- `cups.check(ctx, entitlement)` — يُعيد `True/False` بدون إيقاف
- Caching محلي للـ Resolved Entitlements (TTL بسيط)
- Fallback behavior عند عدم وصول CUPS (fail-open أو fail-closed — قرار تشغيلي)

**قاعدة صارمة:**
Extension لا تقرأ Subscription. تقرأ Resolved Entitlements فقط.
`ctx.entitlements["atlas_access"]` — لا `ctx.subscription.plan`.

### ما لا يُبنى
- لا Atlas فعلي
- لا منطق Billing داخل Extension

### كيف تعرف أنها انتهت
```python
# بوت يعمل على Titan + CUPS Extension
# Starter: لا يملك atlas_access
@bot.command("atlas")
async def use_atlas(ctx):
    if not await cups.require(ctx, entitlement="atlas_access"):
        return  # ← يصل هنا لمستخدم Starter
    # ← لا يصل هنا إلا بعد Phase 3
```

---

## Phase 3 — Billing + دورة حياة الاشتراك

**الهدف:** المستخدم يدفع، النظام يعرف، Entitlements تتغيّر.

### ما يُبنى

**Billing Integration:**
- ربط بمزوّد دفع (يُحدَّد: Telegram Stars / Stripe / غيره)
- Business Events:
  - `PaymentSucceeded` → Subscription تُفعَّل → Entitlement Resolution يُشغَّل
  - `PaymentFailed` → grace period
  - `SubscriptionExpired` → frozen → Starter

**Subscription Lifecycle:**
```
trial → active → grace → frozen → expired → Starter
```
- كل انتقال يُطلق Entitlement Resolution من جديد
- Cache يُبطَل عند كل تغيير حالة

**Trial Flow:**
- 3 أيام تُفتح تلقائياً عند أول اشتراك مدفوع
- آلية تمديد بناءً على الاستخدام (العقل، لا الأتمتة الكاملة — يُحدَّد)

**CUPS Bot إضافات:**
- `/upgrade` — يعرض الخطط ويبدأ عملية الدفع
- `/billing` — حالة الاشتراك الحالية

### ما لا يُبنى
- لا Atlas فعلي بعد (الـ Entitlement يُفتح، لكن الـ Feature نفسها Phase 4)
- لا Team بعد

### كيف تعرف أنها انتهت
```
مستخدم يدفع Plus
       ↓ PaymentSucceeded
       ↓ Entitlement Resolution
       ↓ atlas_access = true في Runtime
       ↓ cups.require(ctx, "atlas_access") → يمرر
(حتى لو Atlas نفسه لم يُبنَ بعد)
```

---

## Phase 4 — الـ Entitlements الفعلية

**الهدف:** كل Entitlement يُفتح → شيء حقيقي يحدث.

### ما يُبنى (بالترتيب)

**tier المنفرد:**
1. `atlas_access` → `titan.atlas` يعمل للمستخدمين المؤهَّلين
2. `inspector_level` → `bot.inspect()` يعمل بمستوياته الثلاثة
3. `runtime_visibility` → `bot.health()` يعمل
4. `usage_insights` → `titan.analytics` يعمل
5. `team_access` → Team model، دعوة الأعضاء، Shared Projects

**لكل Entitlement:**
- الـ Feature موجودة في كود المنتج (Capability)
- Extension تفحص الـ Entitlement قبل السماح بالوصول
- الـ Feature تُغلَق بوضوح — لا silent failure

### ما لا يُبنى
- لا رسائل Trial أو تذكيرات (Phase 5)

### كيف تعرف أنها انتهت
```
مستخدم Plus:
  atlas_access = true → Atlas يستجيب
  usage_insights = false → titan.analytics ترفض بوضوح

مستخدم Ultra:
  جميع Entitlements = true → كل الأدوات تعمل
  Team: Core → يستطيع دعوة أعضاء
```

---

## Phase 5 — طبقة التجربة

**الهدف:** المنتج يشعر كما صمّمناه — لا فقط يعمل كما بُرمج.

### ما يُبنى

**CUPS Bot Messaging:**
- رسائل Trial End (مبنية على استخدام فعلي — Data Awareness Moments)
- رسائل الوصول للحد (نجاح، لا عقوبة)
- رسائل Trial Extension إن مُنحت
- رسائل Downgrade (احترام، لا إقناع بالرجوع)

**Relationship-aware messaging:**
- نبرة الرسائل تتغيّر بحسب المرحلة (Starter/Plus/Core/Ultra)
- لحظة Welcome after Upgrade — Ownership Moment
- رسالة عضو الفريق الجديد — Relationship Context Inheritance

**Continuous Value:**
- Atlas يستأنف السياق بصمت
- bot.health() يعمل في الخلفية
- Delight لحظة الذكرى — "هذا المشروع عمره سنة 🎉"

**CUPS-REVIEW-CHECKLIST integration:**
- في هذه المرحلة يُستخدَم الـ Checklist على كل شيء بُني في Phases 1-4
- أي انحراف يُكتشَف هنا — يُصحَّح الآن

### كيف تعرف أنها انتهت
```
مطور يصل لحد مشاريعه Starter:
  يرى: "يبدو أنك بدأت تبني بجد..." ← لا "انتهى الحد"

مطور Ultra يخفّض لـ Core:
  يرى: "كل شيء محفوظ. الطريق مفتوح." ← لا قائمة بما فقد

مطور تنتهي تجربته:
  يرى: "فتحت Atlas 17 مرة..." ← لا "تنتهي تجربتك"
```

---

## ملخص الـ Phases

| Phase | ما يُبنى | المخرج |
|---|---|---|
| 1 | Account + Project + Starter + Entitlement Resolution + API | النظام يعرف من أنت |
| 2 | titan-extension-cups SDK | أي Titan bot يتكامل مع CUPS |
| 3 | Billing + دورة حياة الاشتراك + Trial | المستخدم يدفع والنظام يستجيب |
| 4 | الـ Features الفعلية لكل Entitlement | كل حق مفتوح يُنتج قيمة حقيقية |
| 5 | الرسائل + نبرة التجربة | المنتج يشعر كما صُمِّم |

---

## ما هو خارج النطاق الآن

هذه تُبنى بعد استقرار الـ 5 Phases:

- Dashboard ويب
- SDK متعدد اللغات
- Organization model
- Enterprise Custom Plans
- Lifetime subscriptions
- Webhook بين CUPS وExtension

انظر: `ROADMAP.md` عند إنشائه.

---

> الكود الأول يُكتب في Phase 1.
> كل شيء قبل ذلك — وثائق، قرارات، فلسفة — كان خدمةً للسطر الأول.
