# تحضير عملي — ما بعد تحقيق Userbot Support

**الحالة:** عمل تحضيري (Phase 0.5 → Phase 2). لا كود Userbot/MTProto.
لا ADR نهائي. هذا الملف يكمّل `userbot-support.md` (مُجمَّد الآن كبوابة
كافية) دون توسيعه.

**قاعدة هذا الملف:** أي سؤال معماري جديد يظهر أثناء هذا العمل يُسجَّل
في قسم "أسئلة مسجَّلة" في الأسفل فقط — لا يُفتح نقاش فلسفي جديد، ولا
يُعاد لمس `userbot-support.md`.

---

## 1. Capability Matrix (Phase 0.5)

جدول القدرات الفعلية اليوم في Bot API (بحكم مراجعة الكود: `telegram.py`,
`adapter.py`, `ctx.py`, `bot.py`) مقابل المعروف عن MTProto من توثيق
Telegram العام (لا كود — لا يوجد تنفيذ MTProto في Titan). الحكم في
العمود الأخير مبدئي، يُراجَع فعلياً عند Phase 3 (ADR).

| القدرة | Bot API (منفَّذة في Titan اليوم) | MTProto (معروف من بروتوكول Telegram) | الحكم المبدئي |
|---|---|---|---|
| إرسال رسالة نصية (`sendMessage`) | ✅ `ctx.send`, `ctx.reply`, `Telegram.send_message` | ✅ عبر `messages.sendMessage` | **مشترك** — نفس المعنى: طرف يرسل نصاً إلى محادثة |
| الرد على رسالة محددة | ✅ `ctx.reply` (`reply_to_message_id`) | ✅ عبر `reply_to_msg_id` | **مشترك** |
| تعديل رسالة (`editMessageText`) | ✅ `ctx.edit` | ✅ `messages.editMessage` | **مشترك** |
| حذف رسالة | ✅ `ctx.delete_message` | ✅ `messages.deleteMessages` | **مشترك** |
| إرسال وسائط (صورة/فيديو/ملف/صوت/ملصق/GIF) | ✅ `TelegramAdapter.send_photo/video/document/audio/sticker/animation` | ✅ لكن برفع/معالجة ملفات مختلفة تماماً (chunked upload خاص بـ MTProto) | **يحتاج قراراً في Phase 3** — المعنى الظاهر مشترك (بايت + caption)، لكن آلية النقل مختلفة جذرياً؛ ليس "مشترك تلقائياً" فقط لأن الاسم متطابق |
| حظر/طرد مستخدم | ✅ `ctx.ban_user`, Bot API `banChatMember` (يتطلب صلاحيات إدارية للبوت) | ⚠️ حساب مستخدم عادي لا يملك صلاحيات إدارية بالضرورة — القدرة نفسها موجودة بروتوكولياً، لكن **دلالتها مختلفة** (فعل إداري لبوت مقابل فعل قد يتطلب صلاحية admin لحساب أيضاً) | **خاص بالسياق، ليس بالسطح** — يحتاج توضيحاً في Capability Rules لاحقاً، لا توحيداً أعمى |
| قراءة صلاحيات البوت في شات (`getChatMember` على النفس) | ✅ `ctx.fetch_permissions` | لا معنى مباشر — الحساب ليس "بوتاً له صلاحيات في الشات" بالمعنى نفسه، إنما عضو | **خاص بـ Bot API** |
| أوامر `/command` + قائمة أوامر (`setMyCommands`) | ✅ `bot.command()`, `TelegramAdapter.set_my_commands` | ❌ لا مفهوم "أوامر مُعرَّفة للبوت" في حساب مستخدم عادي | **خاص بـ Bot API بالكامل** — لا تُعمَّم |
| `callback_query` (ضغط زر Inline Keyboard) | ✅ `ctx.callback_data`, `ctx.answer_callback`, `bot.callback()` | ⚠️ لأزرار Bot API نفسها (رسائل من بوت آخر) — تعمل. لكن لا مفهوم أزرار خاص بمحادثات المستخدم العادية | **مشترك جزئياً** — فقط عندما يكون المصدر رسالة بوت تحمل inline keyboard؛ ليس قدرة أساسية للحساب نفسه |
| انضمام/مغادرة أعضاء (`new_chat_members`/`left_chat_member`) | ✅ `ctx.new_members`, `ctx.left_member` | ✅ نفس الحدث بروتوكولياً (`updateChatParticipant` ومشابهاتها) | **مشترك** — نفس المعنى تقريباً |
| مغادرة شات (`leaveChat`) | ✅ `ctx.leave` | ✅ `messages.deleteChatUser` / مكافئ | **مشترك** |
| تثبيت/إعادة توجيه/نسخ رسالة | ✅ `TelegramAdapter.pin_message/forward_message/copy_message` | ✅ موجودة بروتوكولياً | **مشترك على مستوى المعنى** — التنفيذ يختلف لكن الفعل الظاهر واحد |
| **قراءة تاريخ محادثة قديم (history قبل انضمام البوت)** | ❌ لا وجود لهذا في Bot API إطلاقاً (بوت لا يرى الماضي) | ✅ `messages.getHistory` — قدرة أساسية لحساب المستخدم | **خاص بـ MTProto بالكامل** — لا مكافئ في Bot API، لا تُخترع abstraction وهمية |
| قائمة المحادثات (dialogs) | ❌ لا مفهوم "قائمة محادثاتي" لبوت | ✅ `messages.getDialogs` | **خاص بـ MTProto بالكامل** |
| جهات الاتصال | ❌ غير موجود | ✅ `contacts.getContacts` | **خاص بـ MTProto بالكامل** |
| بدء محادثة بدون /start أولاً من الطرف الآخر | ❌ بوت لا يمكنه بدء محادثة مع مستخدم لم يتفاعل معه | ✅ حساب مستخدم يمكنه إرسال رسالة لأي مستخدم (ضمن حدود الخصوصية) | **خاص بـ MTProto** — وله انعكاس على النقطة الأخلاقية/ToS من `userbot-support.md`، لا يُعاد فتحها هنا |

**ملاحظة على الجدول:** هذا **تمهيدي**، وليس Capability Matrix نهائية.
الغرض هنا إثبات أن أغلب "التشابه الظاهر" (وسائط، حظر) يحمل تفاصيل
دلالية مختلفة تستحق حكماً صريحاً لا توحيداً تلقائياً — تماماً ما
حذّر منه `userbot-support.md` بخصوص "الصمت الجديد" عند إخفاء الفروقات
خلف واجهة موحدة.

---

## 2. استكشاف عملي لـ Canonical/Internal Event Model (Phase 1)

### 2.1 ما هو موجود فعلياً اليوم (بحكم الكود لا الافتراض)

`Update` (في `src/titan/update.py`) تخلط فعلياً بين مسؤوليتين مختلفتين
تماماً، مؤكَّد بالقراءة المباشرة:

1. **Parsing خاص بـ Bot API الخام** — `self.message = raw.get("message")`,
   `self.channel_post = raw.get("channel_post")`,
   `self.callback_query = raw.get("callback_query")`, وكل قراءة
   لاحقة لحقول متداخلة (`msg.get("chat")`, `cb.get("from")`,
   `msg.get("new_chat_members")` ...) — هذه كلها معرفة بشكل JSON من
   Telegram Bot API تحديداً، لا معرفة عامة.

2. **نموذج داخلي مبسَّط** يعرضه للباقي: `text`, `chat_id`, `user_id`,
   `username`, `message_id`, `reply_to_message_id`,
   `reply_to_sender_is_bot`, `chat_type`, دوال الفحص
   (`is_message`, `is_callback`, `has_text`).

`Context` (`src/titan/ctx.py`) تستهلك النموذج المبسَّط (رقم 2) في
أغلب الحالات (`self._update.text`, `self._update.user_id`, ...)، لكنها
أيضاً **تلمس raw مباشرة** في مكانين على الأقل: `ctx.callback_data` /
`ctx.callback_id` يقرآن `self._update.callback_query.get("data"/"id")`
مباشرة بدل عبور طبقة مبسَّطة — هذا اكتشاف عملي جديد (لم يكن موثقاً في
`userbot-support.md`) يُسجَّل في قسم الأسئلة أدناه.

### 2.2 مخطط توضيحي (Sketch فقط — غير مُدمَج في الكود)

هذا رسم لما قد يبدو عليه الفصل، لغرض التفكير فقط، **لا التزام بالاسم
أو الشكل النهائي** (يُحسم في الـ ADR):

```python
# مثال توضيحي فقط — ليس كوداً حقيقياً في src/titan

@dataclass(frozen=True)
class MessageEvent:
    text: str | None
    chat_id: int | None
    user_id: int | None
    username: str | None
    message_id: int | None
    reply_to_message_id: int | None
    reply_to_sender_is_bot: bool
    chat_type: str | None

@dataclass(frozen=True)
class CallbackEvent:
    data: str | None
    callback_id: str | None
    chat_id: int | None
    user_id: int | None
    message_id: int | None   # رسالة البوت المرتبطة بالزر

@dataclass(frozen=True)
class MemberEvent:
    kind: Literal["joined", "left"]
    chat_id: int | None
    members: list[dict] | None   # joined
    member: dict | None          # left


class BotApiTranslator:
    """يعرف شكل JSON الخام لـ Bot API فقط. لا يعرفه أحد آخر."""
    def translate(self, raw: dict) -> MessageEvent | CallbackEvent | MemberEvent:
        ...
```

`Context` تبني نفسها من هذه الأحداث الكانونية بدل `Update` الحالية —
لكن هذا **تغيير غير مطلوب تنفيذه الآن**؛ فقط توضيح لما يعنيه "فصل
الترجمة عن النموذج" عملياً بما يكفي لتقييم حجم Phase 2.

---

## 3. أقل Refactor مطلوب لفصل ترجمة Bot API عن Update (Phase 2)

**المبدأ الحاكم (من `userbot-support.md`):** لا تغيير في `CONTRACT.md`
الظاهر، لا تغيير في توقيع `Context` العام. الفصل داخلي بحت.

**الخطوات الدنيا المحددة بعد قراءة الكود الفعلي:**

1. **نقل منطق قراءة JSON الخام** من `Update.__init__` وكل الدوال
   الخاصة (`_user`, `_chat`, `get_message`) إلى دالة/صنف منفصل
   (مثلاً `BotApiTranslator` أو دالة `parse_bot_api_update(raw) -> ParsedFields`)
   يعيد بنية بيانات بسيطة (dataclass أو dict مسطّح) لا تحمل أي منطق
   Telegram إضافي.

2. **`Update` تصبح غلافاً رقيقاً فوق نتيجة الترجمة** — تحتفظ بكل
   الخصائص العامة الحالية (`text`, `chat_id`, ...) كما هي حرفياً (نفس
   الأسماء، نفس القيم المُرجعة) حتى لا ينكسر أي كود مستهلك — لكنها
   تقرأ من الحقول المُترجَمة بدل قراءة `raw` مباشرة في كل property.

3. **إصلاح نقطتَي التسرب في `Context`** — `ctx.callback_data` و
   `ctx.callback_id` يجب أن يقرآ من حقول مُترجَمة (`update.callback_data`,
   `update.callback_id` كخصائص جديدة على `Update`) بدل الوصول المباشر
   لـ `self._update.callback_query.get(...)`. هذا يُغلق نقطة التسرب
   المكتشفة في §2.1 — بدون هذا الإصلاح، أي مترجم مستقبلي لسطح آخر
   سيحتاج إعادة تكرار هذا المنطق بدل الاعتماد على `Update`.

4. **`raw` تبقى متاحة كما هي** (`update.raw`, `ctx.raw`) — للتوافق مع
   أي كود مستهلك حالي يعتمد عليها مباشرة (مثل `_register_identity` في
   `ctx.py` عبر `self._api._me` — غير متأثر، لكنه تذكير أن `raw` جزء
   من العقد الظاهر ولا يُحذف).

5. **لا حاجة لمس `bot.py` (`_handle_update`, `feed_update`)** — نقطة
   الدخول تبقى: `raw dict → Update(raw) → Context(update, api)`. فقط
   الداخل يتغيّر: `Update.__init__` يستدعي المترجم بدل قراءة `raw`
   مباشرة في كل property.

6. **الاختبارات الحالية (831) تبقى معياراً كافياً** — لأن هذا Refactor
   لا يغيّر أي سلوك ظاهر، فنجاح الاختبارات الحالية بلا تعديل هو معيار
   القبول الوحيد المطلوب لهذه الخطوة عند تنفيذها فعلياً.

**تقييم الحجم:** هذا refactor صغير ومحدود (ملف واحد أساساً +
سطرين في `ctx.py`) — لا يستدعي ADR بذاته (اتساقاً مع القرار المسجَّل
في `userbot-support.md`: هذا تنظيف مسؤوليات داخلية، لا كسر عقد). **لم
يُنفَّذ بعد في هذه الجلسة** — هذا وصف دقيق لما سيُنفَّذ عند الشروع في
Phase 2 فعلياً، ليكون جاهزاً للتنفيذ المباشر دون تحليل إضافي.

---

## أسئلة مسجَّلة فقط (بدون توسيع النقاش الآن)

- `ctx.callback_data`/`ctx.callback_id` يقرآن `raw` مباشرة بدل عبور
  `Update` — نقطة تسرب فعلية اكتُشفت في هذه الجلسة، يُصلَح ضمن Phase 2
  (مذكور في §3 بند 3).
- إرسال الوسائط (صور/فيديو/ملفات) قد يبدو "مشترك المعنى" لكن آلية
  النقل (chunked upload في MTProto) مختلفة جذرياً — هل هذا "قدرة
  مشتركة بتنفيذين" أم "قدرتان مختلفتان بواجهة متشابهة"؟ يُحسم في
  Phase 3 (ADR)، غير محسوم هنا.
- حظر/طرد مستخدم: القدرة موجودة بروتوكولياً في الطرفين، لكن دلالتها
  تعتمد على صلاحيات الحساب/البوت في الشات — هل تصنَّف كقدرة "مشتركة
  بشرط" ضمن Capability Rules المستقبلية؟ غير محسوم هنا.
