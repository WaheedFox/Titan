# CUPS — المعمار

كيف تعمل المنظومة. هذا الملف يصف الهيكل، التدفق، والحدود.

---

## مكوّنات CUPS Platform

```
CUPS Platform
├── CUPS Bot           ← الباب الأمامي — كل تفاعل مستخدم يمر هنا
├── Entitlement Engine ← قلب النظام — يُقيّم ما يملكه المستخدم
├── Product Catalog    ← تعريفات المنتجات وEntitlements كل منها (لا auto-discovery)
│   └── Capabilities   ← ما يستطيع المنتج فعله (مستقل عن ما يُسمح للمستخدم)
├── Billing            ← إدارة الدفع والتجديد والتجريب
└── Extensions         ← الجسور بين CUPS والمنتجات
    └── titan-extension-cups  ← التكامل مع Titan
```

**الفصل بين Capability وEntitlement:**
```
Capability  = تعريف داخل المنتج — "ماذا يستطيع البرنامج؟"
Entitlement = تعريف داخل CUPS  — "ماذا يُسمح للمستخدم؟"
```
هذا الفصل يجعل المنتج ينمو (تُضاف Capabilities) بدون أن تتضخم Entitlements.

---

## CUPS Bot — الباب الأمامي

CUPS Bot هو بوت Telegram مبني فوق Titan.
كل تفاعل مع CUPS يمر عبره: تسجيل المشاريع، إدارة الاشتراكات، عرض الخطط.

**لماذا بوت Telegram وليس واجهة ويب؟**
لأن المنظومة كلها داخل Telegram. المستخدم لا يغادر بيئته.
وهذا يُثبّت أن CUPS يأكل طعامه — مبني فوق نفس الأدوات التي يُقدِّمها.

**أوامر أساسية:**
```
/start        ← إنشاء أو استرجاع Account
/addbot       ← تسجيل مشروع جديد → يُعطي project_id
/myprojects   ← عرض المشاريع المسجَّلة
/plan         ← عرض الخطة الحالية والـ Entitlements
/upgrade      ← الترقية لخطة أعلى
/team         ← إدارة الفريق (Core+)
```

---

## تدفق التسجيل — كيف يُسجِّل مطور مشروعه

```
المطور يفتح CUPS Bot
      ↓
/addbot
      ↓
CUPS: "ما اسم المشروع؟ ما نوعه؟"
(titan-framework / bot / mini-app / game)
      ↓
CUPS يُنشئ Project:
{ project_id: "abc123", product: "titan-framework", owner_id: user_id }
      ↓
CUPS Bot يُرسل للمطور:
"مشروعك مسجَّل. project_id: abc123"
      ↓
المطور يضع project_id في الكود:
cups = CUPSGuard(api_key="...", project_id="abc123")
```

لا Bot Token يُرسَل لـ CUPS. لا تسجيل تلقائي. لا magic.

---

## تدفق التحقق من Entitlement — runtime

عندما يطلب مستخدم ميزة مدفوعة:

```
المستخدم يرسل أمراً في البوت
      ↓
Titan يمرر ctx للـ middleware chain
      ↓
CUPSGuard.as_middleware() يُشغَّل
(يستخرج ctx.user_id)
      ↓
CUPSGuard يسأل CUPS Service:
{
  user_id: 123,
  project_id: "abc123",
  entitlement: "advanced_lint"
}
      ↓
CUPS Entitlement Engine يُقيّم:
- هل للمستخدم subscription نشطة للمنتج؟
- ما قيمة "advanced_lint" في اشتراكه؟
      ↓
CUPS يُجيب: { granted: true/false, value: ... }
      ↓
CUPSGuard يُقرر: يكمل next() أو يُوقف ويُبلِّغ المستخدم
```

---

## حدود التكامل — Titan ↔ CUPS

```
ما يحتاجه titan-extension-cups من Titan:

bot.middleware()    ← Extension Point الوحيد (CONTRACT §16)
ctx.user_id         ← لتحديد هوية المستخدم
ctx.reply()         ← للتواصل مع المستخدم عند رفض الـ Entitlement
```

هذا كل شيء. Titan Core لا يعلم بـ CUPS، ولا يحتاج أن يعلم.

**النمط:**
```python
from titan_extension_cups import CUPSGuard

cups = CUPSGuard(api_key="...", project_id="abc123")
bot.middleware(cups.as_middleware())

@bot.command("export")
async def export_data(ctx):
    if not await cups.require(ctx, entitlement="data_export"):
        return  # CUPSGuard أعلم المستخدم وأوقف التنفيذ
    # ... المنطق الفعلي
```

---

## فصل المسؤوليات

| المسؤولية | من يتولاها |
|---|---|
| تعريف Entitlements لكل منتج | CUPS Product Catalog (تعريف يدوي، لا auto-discovery) |
| تقييم ما يملكه المستخدم | CUPS Entitlement Engine |
| تسجيل المشاريع | CUPS Bot |
| إدارة الدفع | CUPS Billing |
| فحص Entitlement في runtime | titan-extension-cups |
| توجيه الـ updates | Titan Core |
| منطق البوت | المطور |

لا مسؤولية تتقاطع. كل طرف يعرف دوره.

---

## هيكل المجلدات

```
products/cups/
├── PHILOSOPHY.md         ← لماذا يوجد CUPS
├── DOMAIN.md             ← تعريفات الكيانات
├── ARCHITECTURE.md       ← هذا الملف
│
└── services/
    ├── titan-framework/
    │   └── ENTITLEMENTS.md   ← Entitlements الخاصة بـ Titan
    │
    ├── bots/             ← مستقبلاً
    ├── mini-apps/        ← مستقبلاً
    └── games/            ← مستقبلاً
```

**قاعدة:**
كل خدمة جديدة تضيف مجلدها تحت `services/` مع ملف `ENTITLEMENTS.md` خاص بها.
لا تغيير في PHILOSOPHY أو DOMAIN أو ARCHITECTURE — إلا إذا تغيّرت المبادئ نفسها.

---

## ما لا يُبنى الآن

هذه الأشياء خارج النطاق الحالي — تُعاد دراستها عند الحاجة الفعلية:

| الشيء | السبب |
|---|---|
| Webhook بين CUPS وExtension | Polling كافٍ في المرحلة الأولى |
| SDK متعدد اللغات | الهدف الآن Python فقط |
| Dashboard ويب | المنظومة داخل Telegram |
| Enterprise Custom Plans | تُضاف لاحقاً كـ Entitlement خاص |
| Lifetime subscriptions | يحتاج دراسة مستقلة |
| Migration CLI | لا ضغط فعلي الآن |
