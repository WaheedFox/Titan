# Investigation: Message Links Protocol (Feature #0)

**الحالة:** تحقيق (نسخة رابعة — الإطار المعماري الصحيح)
**التاريخ:** 2026-07-09
**المرتبط بـ:** ROADMAP.md Feature #0

---

## المبدأ الأساسي — مرة واحدة وبدقة

```
إنشاء الهوية    →  مسؤولية Titan دائماً. لا opt-in، لا تهيئة.
حفظ المحتوى    →  قرار المطور. اختياري تماماً.
```

**العلاقة الصحيحة بين الطبقتين:**

```
الرابط لا يعتمد على وجود أرشيف.
الأرشيف يعتمد على وجود هوية الرسالة.
```

ليس العكس.

---

## ما هذه الميزة؟

**نظام هوية للرسائل التي يُرسلها بوت يعمل تحت Titan.**

كل رسالة يُرسلها البوت عبر `ctx.send()` / `ctx.reply()` تُولَد معها هوية:

```
https://t.me/MyBot/482
```

هذا **Titan Message Address** — بروتوكول Titan فوق Telegram، لا رابط Telegram native.
Telegram لا يحتاج أن يفهمه. من يفهمه: Titan نفسه، Architect AI، أدوات المطور، Titan Official Bot.

**`/link` لا تُنشئ الهوية — تكشفها.**
عندما يرد مستخدم على رسالة البوت بـ `/link`، يحصل على Titan Message Address للرسالة.
هذا يعمل **تلقائياً** بدون أي تهيئة من المطور.

---

## طبقتان، مسؤوليتان مختلفتان

### الطبقة 1: Identity Layer
**المسؤول:** Titan — دائماً، تلقائياً، بدون اختيار

```
ctx.send() / ctx.reply()
        ↓
Titan ينشئ TitanMessageId + يحفظ الربط الأساسي
        ↓
(titan_id, chat_id, telegram_message_id)
```

ما تفعله:
- توليد `TitanMessageId` فريد لكل رسالة
- حفظ الربط الأساسي: `titan_id ↔ (chat_id, telegram_message_id)`
- الاستجابة لـ `/link` وإعادة Titan Message Address

ما لا تفعله:
- لا تحفظ نص الرسالة
- لا تحفظ metadata إضافية
- لا تعرض أي شيء للمستخدم بدون طلب

### الطبقة 2: Archive Layer
**المسؤول:** المطور — اختياري تماماً

ما تُضيفه:
- حفظ نص الرسالة عند الإرسال
- حفظ metadata (sent_at، نوع الشات، ...)
- إتاحة استرجاع محتوى الرسالة عبر Titan Message Address

```python
# بدون Archive Layer — Identity Layer وحدها:
# /link يعمل → يُعيد "https://t.me/MyBot/482"
# النقر على الرابط → Telegram لا يفعل شيئاً (بروتوكول Titan)

# مع Archive Layer — المطور يُفعّلها:
bot.enable_message_archive()  # أو ما شابه — يُحسم في ADR
# /link يعمل بنفس الطريقة
# Titan Official Bot يستطيع الآن استرجاع المحتوى عبر العنوان
```

---

## Identity Layer — التفاصيل

### ما يُخزَّن في Identity Layer (الحد الأدنى)

```python
@dataclass
class TitanMessageIdentity:
    titan_id: int               # المعرّف الفريد — المفتاح
    bot_username: str           # "MyBot"
    telegram_message_id: int    # معرف Telegram (داخل الشات)
    chat_id: int                # الشات
    deleted: bool = False       # هل حُذفت الرسالة من Telegram؟
```

هذا فقط. لا نص، لا وقت، لا chat_type — هذه تنتمي للـ Archive Layer إذا أراد المطور.

### قاعدة الحجز التاريخي

`titan_id = 482` لرسالة محذوفة → `deleted = True`، لكن `482` لا يُعاد تخصيصه أبداً.
الهوية تصف لحظة وجود — الرسالة كانت، وهذه الحقيقة لا تُمحى.

### التخزين التلقائي

Identity Layer تحتاج تخزيناً دائماً تشغله Titan بدون تهيئة من المطور.

المقترح للدراسة: SQLite في مسار ثابت (مثل `.titan/links.db`)، يُنشأ تلقائياً عند أول تشغيل.
المطور لا يكتب شيئاً — التخزين يحدث خلف الكواليس.

---

## Archive Layer — التفاصيل

### ما تُضيفه على Identity Layer

```python
@dataclass
class TitanMessageArchive:
    titan_id: int               # FK → TitanMessageIdentity.titan_id
    text: str | None            # نص الرسالة عند الإرسال
    chat_type: str              # private | group | supergroup | channel
    sent_at: datetime           # وقت الإرسال
    # قابل للتوسع بحسب حاجة المطور
```

### من يستفيد منها؟

- **Titan Official Bot**: يستطيع عرض محتوى الرسالة عند تلقي Titan Message Address
- **Architect AI**: تستعلم عن رسالة بهويتها وتحصل على نصها
- **أدوات المطور**: ربط رسائل بسجلات داخلية مع الوصول للمحتوى

---

## `TitanMessageId` — صيغة التوليد

الخيارات الثلاثة للدراسة في Architecture Discussion:

| الخيار | المثال | مقروء؟ | يكشف الحجم؟ |
|---|---|---|---|
| Auto-increment | `482` | ✅ | ✅ |
| Opaque int (offset عشوائي) | `10482` | ✅ | ❌ جزئياً |
| UUID | `a3f2c1d4-...` | ❌ | ❌ |

Auto-increment يتوافق مع الفلسفة: "الرسالة 482 لـ MyBot" له معنى مقروء. الـ privacy tradeoff يُوثَّق في ADR.

---

## `titan/links` — Domain مستقل

هذه ليست utility — هي بروتوكول وهوية. تستحق domain خاصاً.

```
src/titan/links/
    __init__.py          — public API
    identity.py          — TitanMessageIdentity + Identity Layer
    archive.py           — Archive Layer (اختياري)
    store.py             — storage interface + SQLite default
    handler.py           — /link command handler
    address.py           — بناء Titan Message Address من titan_id
```

**لماذا مستقل وليس ضمن Core؟**
- يحتوي على تخزين — Core لا يتخزّن
- له بروتوكول خاص به
- قابل للإيقاف نظرياً (Archive Layer قابلة للإيقاف، Identity Layer ليست)

---

## Resolver Layer: Titan Official Bot

```
المستخدم يرسل: "https://t.me/MyBot/482"

Titan Official Bot:
  1. يستخرج: bot_username=MyBot, titan_id=482
  2. يتواصل مع MyBot → يستعلم عن Identity أو Archive
  3. يعرض المتاح بحسب ما فعّله المطور
```

- Official Bot ليس مصدر الهوية — هو مستهلك لها
- يعمل كـ resolver للمستخدم العادي الذي لا يملك أدوات المطور
- يستطيع عرض المحتوى فقط إذا كان المطور فعّل Archive Layer
- مشروع مستقل — خارج نطاق v1

آلية التواصل بين Official Bot وبوت المطور (API? webhook مشترك?) تُحسم في Architecture Discussion.

---

## الاكتشافات البنيوية في Titan

### `reply_to_message` غير مستخرج في `Update`

```json
"reply_to_message": {
  "message_id": 789,
  "from": { "is_bot": true, "username": "MyBot", "id": 12345 }
}
```

`Update` في Titan حالياً لا يستخرج هذه البيانات. تغيير بسيط مطلوب.

### `ctx.send()` / `ctx.reply()` يحتاجان intercepting

لإنشاء Identity عند الإرسال، Titan يحتاج `telegram_message_id` من استجابة `send_message`.
الاستجابة موجودة (تُعاد كـ `dict[str, Any]`) — الـ intercepting بسيط داخل Identity Layer.

---

## ملخص للنقاش المعماري

| السؤال | الإجابة |
|---|---|
| ما طبيعة الرابط؟ | Titan Message Address — بروتوكول فوق Telegram |
| هل Identity تحتاج opt-in؟ | لا — تعمل دائماً، تلقائياً |
| متى تُنشأ الهوية؟ | عند إرسال الرسالة |
| ما `/link`؟ | تكشف هوية موجودة |
| ما الاختياري؟ | Archive Layer فقط (حفظ المحتوى + الاسترجاع) |
| أين يعيش الكود؟ | `titan/links` — domain مستقل |
| Resolver Layer متى؟ | مستقبلاً — خارج نطاق v1 |

**قرارات تنتظر النقاش المعماري:**
1. صيغة TitanMessageId (auto-increment vs opaque int)
2. مسار تخزين Identity Layer الافتراضي (`.titan/links.db`؟)
3. واجهة تفعيل Archive Layer من المطور
4. سلوك `/link` إذا اكتشف رسالة سبقت تفعيل الميزة (retroactive registration؟)
5. آلية تواصل Titan Official Bot مع بوت المطور (مستقبلي)

---

*هذا الملف تحقيق — لا قرارات نهائية. القرارات في ADR.*
