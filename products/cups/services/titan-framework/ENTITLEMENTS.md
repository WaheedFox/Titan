# titan-framework — Entitlements

هذا الملف يُعرِّف كل Entitlement لمنتج `titan-framework` ويُترجم كل خطة إلى قيم فعلية.

---

## المبدأ الأساسي

**المكتبة نفسها — `pip install titan-lib` — مجانية دائماً.**
ما يُفتح بالاشتراك هو **طبقة الأدوات المحيطة**: أدوات المطور، أدوات الفريق، أدوات الإنتاج.
الفرق: Titan يعمل للجميع. CUPS يُفتح مستويات عمل أعلى.

---

## ما هو مجاني دائماً (Starter Core)

هذه المكوّنات متاحة لكل مستخدم Titan — بلا اشتراك، بلا قيود:

| المكوّن | الوصف |
|---|---|
| `Titan`, `Router`, `Context` | الإطار الأساسي |
| `Middleware`, `MiddlewareChain` | سلسلة التنفيذ |
| `Adapter`, `Update` | ترجمة Telegram updates |
| `Telegram` client | الاتصال بـ Telegram API |
| `Message`, `Sender`, `Chat` | نماذج البيانات الأساسية |
| `InlineKeyboard`, `InlineButton` | لوحة المفاتيح |
| `TitanError`, `TelegramError` | هرمية الأخطاء |
| `titan.extras` (AskManager, AliasMap) | أدوات مساعدة |
| `titan.recipes.welcome` | الوصفة الأساسية |
| `titan.validation` | التحقق من صحة الـ handlers |
| `titan.lifecycle` | إدارة polling والإيقاف الآمن |
| `titan.privacy` | بروتوكول خصوصية البيانات — متاح دائماً لأنه التزام قانوني |
| `titan.migration` | مساعد الترحيل — متاح دائماً لتخفيض حاجز الانتقال لـ Titan |

---

## قائمة Entitlements

### الحدود الكمية

| Entitlement | النوع | الوصف |
|---|---|---|
| `max_bots` | integer | عدد المشاريع المسجَّلة في CUPS |
| `team_members_limit` | integer | عدد أعضاء الفريق (`0` = لا فريق) |

### أدوات المطور

| Entitlement | النوع | الوصف |
|---|---|---|
| `atlas_access` | boolean | `titan.atlas` — الذاكرة المعمارية والـ AI assistant |
| `lint_advanced` | boolean | `bot.lint()` — قواعد lint متقدمة |
| `inspector_access` | boolean | `bot.inspect()` — لقطة حالة البوت (BotSnapshot) |
| `playground_access` | boolean | `titan.playground` — بيئة اختبار البوت |
| `profiler_access` | boolean | `titan.profiler` — قياس الأداء |
| `timeline_access` | boolean | `titan.timeline` — سجل التطور المعماري |

### أدوات الإنتاج

| Entitlement | النوع | الوصف |
|---|---|---|
| `health_access` | boolean | `bot.health()` — فحص صحة البوت |
| `links_access` | boolean | `titan.links` — بروتوكول روابط الرسائل |

### Team

| Entitlement | النوع | الوصف |
|---|---|---|
| `team_access` | boolean | إمكانية إنشاء فريق وإضافة أعضاء |

### الدعم

| Entitlement | النوع | الوصف |
|---|---|---|
| `analytics_access` | boolean | إحصاءات وتقارير الاستخدام |
| `priority_support` | boolean | دعم ذو أولوية |

---

## ترجمة الخطط إلى Entitlements

### Starter — مجاني

```json
{
  "max_bots": 3,
  "team_members_limit": 0,
  "atlas_access": false,
  "lint_advanced": false,
  "inspector_access": false,
  "playground_access": false,
  "profiler_access": false,
  "timeline_access": false,
  "health_access": false,
  "links_access": false,
  "team_access": false,
  "analytics_access": false,
  "priority_support": false
}
```

**ما يعمل:** الإطار كاملاً — بناء بوتات، نشر، تشغيل. بلا قيود على الإطار نفسه.
**ما لا يعمل:** أدوات المطور المتقدمة، أدوات الإنتاج، الفريق.

---

### Plus — $4.99/شهر | $49/سنة

```json
{
  "max_bots": 10,
  "team_members_limit": 0,
  "atlas_access": true,
  "lint_advanced": true,
  "inspector_access": true,
  "playground_access": true,
  "profiler_access": true,
  "timeline_access": true,
  "health_access": false,
  "links_access": false,
  "team_access": false,
  "analytics_access": false,
  "priority_support": false
}
```

**ما يفتح:** حزمة أدوات المطور كاملة — Atlas، Lint، Inspector، Playground، Profiler، Timeline.
**الجمهور:** المطور الجاد الذي يبني مشاريع متعددة ويهتم بجودة الكود.

---

### Core — $7.99/شهر | $79/سنة

```json
{
  "max_bots": 20,
  "team_members_limit": 5,
  "atlas_access": true,
  "lint_advanced": true,
  "inspector_access": true,
  "playground_access": true,
  "profiler_access": true,
  "timeline_access": true,
  "health_access": true,
  "links_access": true,
  "team_access": true,
  "analytics_access": false,
  "priority_support": false
}
```

**ما يفتح فوق Plus:** أدوات الإنتاج (Health، Links)، وإمكانية الفريق (حتى 5 أعضاء).
**الجمهور:** الفرق الصغيرة والمشاريع الإنتاجية الجادة.

---

### Ultra — $14.99/شهر | $149/سنة

```json
{
  "max_bots": 100,
  "team_members_limit": 20,
  "atlas_access": true,
  "lint_advanced": true,
  "inspector_access": true,
  "playground_access": true,
  "profiler_access": true,
  "timeline_access": true,
  "health_access": true,
  "links_access": true,
  "team_access": true,
  "analytics_access": true,
  "priority_support": true
}
```

**ما يفتح فوق Core:** Analytics، Priority Support، فريق حتى 20 عضواً.
**الجمهور:** الشركات والمحترفون.

---

## ⚠️ قرار معلَّق — يحتاج موافقة

**الأسئلة الخمسة التي تحدد "الذهب" النهائي:**

### ١. هل Titan منتج واحد أم منتجات منفصلة؟

**المقترح الحالي:** منتج واحد (`titan-framework`) بـ Entitlements داخلية.

**البديل:** منتجات منفصلة (`titan-core` مجاني، `titan-developer-tools` مدفوع).

*البديل يُعقِّد تجربة المستخدم — منتج واحد أبسط وأوضح.*

---

### ٢. هل `health_access` في Core أم Plus؟

`bot.health()` أداة تشخيص — قد يحتاجها أي مطور جاد، لا فقط الفرق.

- **Core (الحالي):** يُشير لكونها production monitoring للفرق.
- **Plus (البديل):** يُشير لكونها developer tool.

---

### ٣. هل `links_access` في Core أم Plus؟

`titan.links` (LinksManager، SqliteMessageStore) — بروتوكول متخصص لربط الرسائل.

- **Core (الحالي):** استخدامه production يبرر وضعه مع أدوات الإنتاج.
- **Plus (البديل):** أداة مطور متقدمة، ليست production بالضرورة.

---

### ٤. هل `inspector_access` و`timeline_access` مفيدان للـ Starter؟

الـ Inspector (`bot.inspect()`) يُعطي لقطة حالة البوت — مفيد للتطوير.
الـ Timeline سجل معماري — ذو قيمة لكن ليس ضرورياً للمبتدئ.

---

### ٥. ما حد `max_bots` الذي يشعر "بالضيق" في Starter بشكل عادل؟

3 مشاريع كافية للتجربة الشخصية. لكن:
- هل 3 صحيح أم 5 يكون أعدل؟
- هل max_bots يُحسب per-product أم across all products في CUPS؟

---

## كيف يستخدم الكود Entitlements

```python
# ✅ صح — يفحص Entitlement محدداً
if not await cups.require(ctx, entitlement="atlas_access"):
    return

# ✅ صح — قيمة كمية
limit = await cups.value(ctx, entitlement="max_bots")

# ❌ خطأ — لا تفحص Plan مباشرةً
if user_plan == "plus":
    ...
```

---

## إضافة Entitlement جديد

1. أضف السطر في جدول القائمة أعلاه (الاسم، النوع، الوصف).
2. حدد قيمته في كل خطة من الأربع.
3. Starter يحصل على القيمة الأكثر تقييداً (`false` أو `0`).
4. استخدم الاسم مباشرةً في الكود.

**لا تغيير في اسم الخطة. لا تغيير في CUPS بنية.**
هذا هو سبب فصل Entitlement عن Plan.
