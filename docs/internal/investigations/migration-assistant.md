# تحقيق — Migration Assistant

**الحالة:** مكتمل — القرار في [docs/decisions/007-migration-assistant.md](../decisions/007-migration-assistant.md)  
**تاريخ:** 2026-07-08  
**الميزة:** Migration Assistant (#2)

---

## 1. المشكلة

هذه الميزة تشمل **مسارَين منفصلَين** يجمعهما اسم واحد. يجب تحديد حدود كل منهما قبل أي تصميم.

---

### المسار أ — Framework Migration

**من منظور المطور:**  
"أعمل على بوت مكتوب بـ PTB أو aiogram أو telebot، وأريد الانتقال إلى Titan. أعرف أن المفاهيم متشابهة، لكنني لا أعلم أين الفروقات غير الواضحة ولا كيف أترجم كودي الحالي."

**الأهمية الاستراتيجية:** هذا ليس مجرد developer tool — هو أحد الأسباب الأساسية لوجود Titan. نمو مجتمع Titan يعتمد على قدرة مطوري Telegram الحاليين على الانتقال إليه.

---

### المسار ب — Titan Version Migration

**من منظور المطور:**  
"صدر Titan v2. لا أعلم ماذا تغيّر ولا كيف أُحدّث كودي بأمان."

**الحالة الحالية:** Titan في مرحلة مبكرة. لا توجد إصدارات متعددة بعد، ولا breaking changes موثّقة. المسار موجود لكنه ليس حاجة آنية.

---

## 2. ما يوجد حالياً في الـ Core

### خريطة المقابلات (Framework → Titan)

| المفهوم | PTB | aiogram | telebot | **Titan** |
|---|---|---|---|---|
| **الكلاس الرئيسي** | `Application` | `Dispatcher` | `TeleBot` | `Titan` |
| **تسجيل أمر** | `app.add_handler(CommandHandler('x', fn))` | `@dp.message(Command('x'))` | `@bot.message_handler(commands=['x'])` | `@bot.command('x')` |
| **حدث عام** | `MessageHandler(filters.TEXT, fn)` | `@dp.message(F.text)` | `@bot.message_handler(content_types=['text'])` | `@bot.on('message')` |
| **Callback** | `CallbackQueryHandler(fn, pattern='x')` | `@dp.callback_query(F.data == 'x')` | `@bot.callback_query_handler(...)` | `@bot.callback('x')` |
| **السياق** | `update + context` (منفصلَان) | `message: Message` (النوع مباشر) | `message` | `ctx` (موحّد) |
| **الرد** | `update.message.reply_text('hi')` | `message.answer('hi')` | `bot.reply_to(message, 'hi')` | `ctx.reply('hi')` |
| **التنظيم** | لا يوجد مدمج | `Router` | لا يوجد مدمج | `Router` |
| **Middleware** | `Application.post_init` / ConversationHandler | Middleware stack | لا يوجد | `@bot.middleware` |
| **Error handler** | `app.add_error_handler(fn)` | `@dp.errors()` | try/except يدوي | `@bot.error_handler` |
| **التشغيل** | `app.run_polling()` | `await dp.start_polling(bot)` | `bot.polling()` | `bot.run()` |

---

### نقاط الاحتكاك الحقيقية (الفروقات غير الواضحة)

هذه ليست مجرد فروق في الـ syntax — بل في نموذج التفكير:

**1. handler واحد لكل command/callback_data (قاعدة Titan)**  
PTB و aiogram يسمحان بعدة handlers على نفس الأمر عبر الـ priorities/filters.  
Titan يرمي `TitanError` عند التكرار.  
→ المطور القادم من PTB قد يسجّل handler مزدوجاً ويتعجب من الخطأ.

**2. توحيد السياق في `ctx`**  
في PTB: `update.message` و`context.bot` منفصلَان.  
في aiogram: النوع يحدد السياق (`message: Message`, `query: CallbackQuery`).  
في Titan: كل شيء في `ctx` — `ctx.text`, `ctx.callback_data`, `ctx.reply()`.  
→ المطور يحتاج إعادة تفكير في كيفية الوصول للبيانات.

**3. `ctx.permissions` ليست متاحة مباشرةً**  
تحتاج `await ctx.fetch_permissions()` صراحةً.  
في PTB: `context.bot.get_chat_member()` صريحة هي الأخرى.  
في aiogram: مماثل.  
→ ليست مفاجأة كبيرة، لكن تحتاج توثيقاً.

**4. الـ callback routing**  
Titan يفصل `@bot.callback('data')` (محدد) عن `@bot.on('callback')` (عام).  
aiogram يستخدم `F.data == 'x'` أو `F.data.startswith('x')` للـ filtering.  
PTB يستخدم `pattern` regex.  
→ Titan لا يدعم الـ patterns — يحتاج `callback_data` دقيقة.

**5. الـ middlewares**  
Titan: سلسلة واحدة تعمل على كل update.  
aiogram: outer/inner middleware مع granularity عالية.  
PTB: لا middleware system حقيقي.  
→ المطور القادم من aiogram قد يبحث عن per-handler middleware.

---

## 3. هل المشكلة حقيقية؟

### المسار أ (Framework Migration)
**نعم — ومؤثرة استراتيجياً.**  
بدون دليل انتقال واضح، المطور القادم من PTB أو aiogram:
- يعثر في الفروقات غير الواضحة.
- قد يعود لإطاره الأصلي لأن التعلم يبدو مرتفع التكلفة.
- لا يجد نقطة دخول واحدة تقول: "أنت في هذا المكان، وTitan هنا."

### المسار ب (Version Migration)
**حقيقية من حيث المبدأ — لكن ليست حاجة آنية.**  
Titan لا يملك بعد:
- إصدارات متعددة بـ breaking changes موثقة.
- مطورين متضررين من ترقية.

التحقيق في هذا المسار الآن يعني بناء أداة لمشكلة لم تحدث بعد.

**الاستنتاج:** المسار ب يُؤجَّل بوعي حتى يوجد v2 حقيقي مع breaking changes. المسار أ هو الأولوية.

---

## 4. الحد الأدنى من التدخل

**الجدول:**

| التدخل | التكلفة | متى يُستخدم |
|---|---|---|
| دليل انتقال نصي (docs فقط) | صفر سطح | إذا كانت المشكلة توثيق بحت |
| `titan.migration` module يُرجع خريطة مقابلات | سطح صغير | إذا كان المطور يحتاج الإجابة برمجياً |
| CLI تفاعلي يفحص الكود | سطح كبير جداً | إذا كانت المشكلة تحويل كود تلقائي |
| Runtime hints في الأخطاء | مدمج في Core | إذا كانت المشكلة رسائل خطأ غير مفهومة |

**التقييم الأولي:**  
المشكلة الحقيقية هي: المطور القادم من إطار آخر يرتكب أخطاء تنبع من افتراضات خاطئة يصعب تتبعها.

هذا يشير إلى:
- دليل انتقال موثَّق بشكل رسمي (لا كود جديد)
- أو رسائل خطأ أوضح في Titan تشير صراحةً للفرق ("If you're migrating from PTB...")
- أو كليهما

الحل الأغلى (CLI / code scanner) يحل مشكلة التحويل التلقائي — لكن هذه ليست المشكلة الأساسية. المشكلة هي الفهم، لا الأتمتة.

---

## 5. التوترات المعمارية

### التوتر 1 — هل هذا كود أم توثيق؟

Migration Assistant: هل هو:
- **أ) `titan.migration` module** — كلاس أو دوال تُرجع mapping tables، framework differences، migration checklist؟
- **ب) ملفات توثيق في `docs/migration/`** — أدلة نصية لكل framework؟
- **ج) الاثنان** — docs للبشر + module للأدوات (Architect AI مستقبلاً)؟

**التوتر الحقيقي:** الـ module يضيف سطحاً للـ contract. الـ docs لا تُضيف شيئاً للـ contract لكنها لا تقبل الـ automation.

### التوتر 2 — ما عمق التغطية؟

كم framework يُغطّي v1؟
- PTB فقط (الأكثر شيوعاً)؟
- PTB + aiogram؟
- PTB + aiogram + telebot؟

كلما زادت الأطر المغطّاة كلما زادت التكلفة وزادت التقادم. خاصة أن PTB v20 مختلف جداً عن PTB v13.

### التوتر 3 — هل Framework Migration = "كيفية الترحيل" أم "لماذا Titan أفضل"؟

دليل الانتقال يمكن أن يكون:
- **تقنياً بحتاً:** هذا الكود بـ PTB يصبح هكذا بـ Titan.
- **مقارنةً فلسفيةً:** Titan يختار X، PTB يختار Y، الفرق في التصميم هو Z.

الأول يساعد المطور على التحويل. الثاني يساعده على الفهم العميق — وهو ما يجعله يبقى.

---

## 6. الأسئلة المفتوحة للنقاش المعماري

1. **Module أم docs؟** — هل Migration Assistant كود في `titan.migration` أم توثيق في `docs/migration/`، أم كليهما بأدوار مختلفة؟

2. **نطاق الأطر في v1** — PTB + aiogram + telebot؟ أم نبدأ بـ PTB فقط باعتباره الأكثر شيوعاً وأعمق تغطيةً؟

3. **المسار ب (Version Migration)** — تأجيل رسمي بوعي حتى يوجد v2 حقيقي، أم وضع بنية تحتية الآن (policy document + CHANGELOG convention)?

4. **Runtime hints** — هل تُضاف رسائل خطأ توجيهية للمطورين القادمين من frameworks أخرى داخل TitanError أو رسائل الـ conflict؟ هذا يمس الـ Core مباشرةً.

5. **الجمهور المستهدف** — هل دليل الانتقال يُكتب لمطور PTB لا يعرف Titan أصلاً؟ أم لمطور يعرف Titan ويريد ترحيل كود موجود؟

---

## 7. التقييم الأولي

**الفرق الجوهري عن Interactive Inspector و Project Health:**  
Inspector و Health كانا **كوداً جديداً في الـ Core**.  
Migration Assistant قد يكون **توثيقاً بالكامل** — وهذا خيار مشروع وليس نقصاً.

**أسبقية المسارين:**

| المسار | الأولوية | التوقيت |
|---|---|---|
| Framework Migration | عالية — استراتيجية | الآن |
| Version Migration | متوسطة — ضرورية | عند وجود v2 |

**القرار بعد النقاش المعماري:**

Migration Assistant طبقتان في v1:

**الطبقة 1 — Documentation Layer:**
```
docs/migration/
    README.md          — نقطة الدخول (اختر إطارك)
    from-ptb.md        — فلسفة + friction points + لا مقابل مباشر
    from-aiogram.md    — فلسفة + friction points + لا مقابل مباشر
    from-telebot.md    — فلسفة + friction points + لا مقابل مباشر
```

**الطبقة 2 — Migration Knowledge API:**
```
src/titan/migration/
    __init__.py        — public API: frameworks(), concepts(), compare()
    _data.py           — بيانات الـ mappings (private — يقرأها فقط __init__)
    models.py          — ConceptMapping dataclass
```

**المسار ب (Version Migration):** مؤجَّل بوعي — يُسجَّل في الـ Roadmap.  
**المستوى 3 (Code scanner/CLI):** مؤجَّل بوعي — يُسجَّل في الـ Roadmap.
