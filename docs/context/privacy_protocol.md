# Titan Privacy Protocol Context

هذا الملف يحتوي على السياق المعتمد قبل متابعة العمل وهو ملخص المناقشات الطويلة وبعض من التحقيقات


## تعليمات قراءة هذا الملف

هذا الملف ليس مجرد سجل محادثة، بل سياق معماري معتمد.

القواعد:
- القرارات الموجودة تحت "القرارات غير القابلة للنقاش" تعتبر قرارات مثبتة.
- سجل المحادثات الموجود لاحقاً يستخدم لفهم سبب القرارات، وليس لإعادة فتحها.
- إذا وجد تعارض بين السجل والقرارات النهائية، تُقدّم القرارات النهائية.
- قبل تعديل أي ADR أو كود، راجع الكود الفعلي للتأكد من توافق التنفيذ مع العقد.
- لا تعُد لمناقشة قرارات محسومة إلا إذا ظهر تعارض حقيقي في الكود.


## الحالة المعمارية الحالية

ADRs الحالية:

- ADR-015:
  Data Lifecycle Responsibility
  يحدد مسؤولية Titan عن البيانات التي تنشئها وتديرها.

- ADR-016:
  User Data Registry و erase_user
  يحدد طريقة اكتشاف وإدارة User Data Modules.

- ADR-017:
  Reserved Privacy Commands
  يحدد حجز /mydata و /forgetme وضمان عدم تجاوز العقد.

- ADR-018:
  Permanent Resource Identity
  يحدد طبيعة Links و titan_id كهوية مورد دائمة.

الاعتماد:

ADR-015
   ↓
ADR-016
   ↓
ADR-017

ADR-018 مستقل، لكنه مرتبط بمفهوم التخزين الدائم والهوية.


## الحالة الحالية

تم الانتهاء من:
- التحقيق الأولي حول User Privacy & Erasure Protocol.
- الفصل بين User Data و Protocol Storage.
- تثبيت Links كـ Permanent Resource Identity.
- كتابة ADR-015 إلى ADR-018.

## القرارات غير القابلة للنقاش

1. titan_id:
   - دائم.
   - لا يُحذف.
   - لا يُعاد استخدامه.
   - حذف الرسالة يغير حالة المورد فقط.

2. Links:
   - ليست User Data.
   - ليست ضمن erase_user.
   - Identity Layer إلزامية.
   - Archive Layer منفصلة و opt-in.

3. erase_user:
   - عقد عام.
   - يمس User Data فقط.
   - لا يمس Protocol Identity.

4. /mydata:
   - أمر محجوز.
   - يعرض كل ما تعرفه Titan عن المستخدم.
   - التقرير غير قابل للتلاعب من hooks.

5. /forgetme:
   - يحذف User Data بالكامل.
   - لا يمكن للمطور تعطيله أو اعتراضه.
   - لا pre-hook قبل الحذف.

## القرارات التي تحتاج متابعة

- تنفيذ UserDataRegistry.
- تنفيذ UserDataModule Protocol.
- تنفيذ reserved commands.
- حالات الفشل المتوقعة.
- مراجعة hooks والتنفيذ.

## آخر حالة للكود وبعض من سجل محادثاتنا السابقة


## مبدأ التنفيذ القادم

الهدف ليس فقط توفير API للخصوصية، بل جعل انتهاك العقد صعباً بالتصميم.

المطلوب:
- المسار الصحيح يكون تلقائياً للمكونات الرسمية.
- المسار الخاطئ يفشل بوضوح.
- لا توجد hooks تسمح بتجاوز الحذف أو إخفاء الحقيقة.
- لا توجد مناطق تخزين User Data داخل Titan بدون عقد معلن.


[Agent:
Set up the imported project
The user just imported this project from a GitHub repository. It could be anything — an app to run on Replit, a library, a fork to study, code to reuse — so the first thing to do is ask what they want; everything after depends on the answer.

What would you like to do with Titan?
Goal
Make changes to the library code
Additional comments
We have decided to postpone Userbot Support.
This is not cancelled, only deferred.
The feature will be revisited only if one of the following happens:
There is a real practical need inside Titan itself.
There is significant demand from users or contributors.
It becomes a planned goal for Titan v2.
Until then, do not continue implementing Userbot-related code, abstractions, adapters, MTProto integration, or architectural preparations beyond what already exists.
Please record this decision in the appropriate place (preferably the roadmap or the investigation notes) as an explicit project decision, so future work does not accidentally resume it without a conscious decision.
From this point forward, our focus returns to Titan Core and the current roadmap.
I need to move Userbot Support from "ميزات مخططة — قيد التحقيق المعماري" to "مؤجلة بوعي" in the roadmap, and stamp the investigation file with the deferral decision.

Now I'll stamp the investigation file with the deferral decision at the top.

انا:
ننتقل الآن إلى الخطة #11 (User Privacy & Erasure Protocol).

ابدأ بنفس الأسلوب الذي اتبعناه سابقاً، لكن بنطاق صغير ومحدد:

إنشاء وثيقة تحقيق أولية تحدد النطاق فقط.
تحديد ما الذي يعتبر "بيانات مستخدم" داخل Titan.
تحديد حدود مسؤولية Titan وما الذي لا تتحمل مسؤوليته.
اقتراح واجهة عامة (Public API) أولية فقط، دون تنفيذ أو Refactor.
تسجيل أي أسئلة معمارية حقيقية تظهر أثناء التحقيق، لكن لا توسّع الوثيقة بلا داعٍ.
لا تبدأ كتابة الكود بعد. لا تفتح ADR. لا تعيد تصميم أجزاء أخرى من Titan.

أريد وثيقة عملية تساعدنا على البدء بالتنفيذ لاحقاً، لا تحقيقاً مفتوحاً يمتد بلا نهاية.

قبل اقتراح أي تصميم، أريد مراجعة عملية لتجارب وشكاوى المطورين المتعلقة بالخصوصية في أشهر مكتبات Telegram وأطر العمل، مع التركيز على المشكلات المتكررة لا الحالات الفردية.

لا نريد تقليد هذه المكتبات، بل نريد اكتشاف الأنماط التي تسببت في ضعف الخصوصية أو تعقيدها، ثم استخدام هذه النتائج لبناء تصميم Titan بحيث يزيل أسباب المشكلة من الجذر، لا أن يضيف حلولاً سطحية فوقها.

Agent:
لديّ كل ما أحتاجه. أكتب الوثيقة الآن.

Now I'll update the ROADMAP to link the new investigation file for #11, and record the key architectural insight in memory.

الوثيقة جاهزة في docs/internal/investigations/user-privacy-erasure.md، والـ ROADMAP محدَّث.

ما تضمّنته الوثيقة
مراجعة المكتبات الأخرى كشفت ثلاثة أسباب جذرية متكررة في PTB وaiogram وtelebot:

الإطار لا يُميّز بين بيانات عبور وبيانات مُحتجزة
التخزين سهل، الحذف معدوم — عدم التماثل هو المشكلة
المطوّر لا يعرف ما الذي يحتفظ به الإطار بالنيابة عنه
جرد بيانات Titan الفعلي — ثلاث طبقات واضحة:

بيانات عبور (ctx/models): تعيش update واحداً، لا مسؤولية خاصة
في الذاكرة (banned_users, AskManager): آلية حذف موجودة جزئياً لكن بلا TTL
على الديسك (Links SQLite): الطبقة الحقيقية للمشكلة — mark_deleted يضع flag فقط، لا حذف حقيقي، لا erase_user
الواجهة المقترحة أولياً:

await bot.erase_user(user_id=123456789)
await bot.erase_chat(chat_id=...)
السؤال المعماري الأهم قبل فتح ADR: أين تعيش erase_user؟ Core لا تعرف عن extras وعن links — ثلاثة خيارات مطروحة في الوثيقة، الجواب يحدد شكل الـ API كلياً.

انا:
أوافق أن السؤال عن AskManager يحتاج حسم، لكن لا أريد أن يصبح التصميم مرتبطاً به وحده.

القرار الحقيقي ليس: "هل AskManager يسجل نفسه تلقائياً أم لا؟"

القرار الحقيقي هو:

"كيف تعرف Titan أن Module معين أصبح مسؤولاً عن User Data؟"

AskManager هو أول مثال فقط.

أريد أن نثبت القاعدة العامة:

أي Module First-party داخل Titan ويملك User Data يجب أن يدخل Registry تلقائياً.
أي Module خارجي يريد الدخول في نظام /mydata و/forgetme يجب أن يعلن نفسه عبر API واضحة.
لا أريد أن تعتمد Titan على أن المطور يتذكر إضافة كل شيء يدوياً للمكونات الرسمية.
لذلك أرى أن AskManager يجب أن يُعامل كـ First-party Module:

عند ربطه بالطريقة الرسمية مع Titan (مثل middleware registration أو أي نقطة lifecycle مناسبة) يتم تسجيله تلقائياً.

لكن Module خارجي لا يمكن اكتشافه سحرياً، لذلك يحتاج declare_user_data أو ما يعادلها.

الفصل المهم:

First-party: Titan تعرفه → التسجيل تلقائي.

Third-party: Titan لا تعرفه → الإعلان مطلوب.

هذا يحافظ على هدف ADR-016: المسار الصحيح يجب أن يكون الأسهل، وليس أن نضع مسؤولية الخصوصية على ذاكرة المطور.

أيضاً أريد إضافة نقطة قبل التنفيذ:

يجب مراجعة كل ما يتعلق بـ "غير قابل للتحايل" في الكود، وليس فقط الوثيقة.

بالنسبة لـ /mydata:

التقرير يجب أن يكون مبنياً من Registry الحقيقي.
أي hook للتنسيق يجب ألا يستطيع حذف بيانات من التقرير.
المطور يستطيع تغيير العرض فقط، وليس الحقيقة.
بالنسبة لـ /forgetme:

لا يوجد pre-hook يستطيع منع أو إيقاف المحو.
أي callback يكون بعد اكتمال المحو فقط.
يجب أن يكون هناك ضمان أن المحو يشمل كل User Data المسجلة في Titan.
بالنسبة للأوامر: أريد أن يبقى /mydata و /forgetme محجوزين بنفس صرامة /link. لا override. لا disable. لا إعداد يخفيهما.

وأريد إضافة نقطة أخرى لـ ADR-017: إذا حاول المطور التحايل عبر تسجيل أمر بنفس الاسم، يجب تحديد السلوك في الكود بوضوح: هل exception؟ هل رفض التسجيل؟ المهم أن النتيجة لا تكون صامتة.

الهدف ليس جعل المطور عدواً، بل جعل الطريق الخطأ غير مريح والطريق الصحيح تلقائياً.

بعد تثبيت هذه القاعدة نبدأ التنفيذ، لأن AskManager مجرد أول مستخدم للنظام وليس النظام نفسه.

Agent:
Finalizing design principles
القرار واضح ومُحكم. أُحدِّث ADR-016 وADR-017 لتثبيت هذه القواعد قبل التنفيذ.

القرار واضح. أُحدِّث ADR-016 بالفصل بين First-party وThird-party، وأُضيف للـ ADR-017 ضمانات التنفيذ الثلاثة.

أكملت §1 فقط — أُضيف ضمانات /mydata و/forgetme الآن.

التعديلات الثلاثة مكتملة. ملخص ما تغيّر:

ADR-016 — §4 أُعيد كتابته بالكامل

الفصل الآن قائم على قاعدة واحدة: هل Titan تعرف هذا الـ module بالاسم؟

First-party ثابت (يُنشأ في __init__()) → تسجيل غير مشروط
First-party اختياري (مثل AskManager) → تسجيل تلقائي عند الربط بالطريقة الرسمية (bot.enable_ask() أو ما يعادلها) — لا declare_user_data منفصل
Third-party (كود المطوّر) → declare_user_data() مرة واحدة
القاعدة المُثبَّتة: مسؤولية الخصوصية لا تُوضَع على ذاكرة المطوّر للمكوّنات الرسمية.

ADR-017 — ثلاثة إضافات:

§1 — سلوك التعارض: الخطأ ليس صامتاً ولا مبهماً — رسالة تُسمّي الأمر المحجوز وسببه، تُكتشف من كل مسار (@bot.command, bot.include, @router.command). مُثبَّت في الكود عبر _command_sources منذ __init__().

§4 — /mydata hook: report الذي تستلمه الـ hook هو MappingProxyType — read-only بطبيعته. محاولة حذف مفتاح أو تعديل قيمة ترفع TypeError من Python مباشرةً. المطوّر يتحكم في كيف يُعرض التقرير — لا في ماذا يحتوي.

§4 — /forgetme hook: الترتيب مُثبَّت في الكود: erase_user() أولاً وبالكامل، ثم on_forgetme_complete. لا on_forgetme_before ولا on_forgetme_condition في API — الغياب قصد لا سهو.

الوثائق الآن تصف بنية يمكن ترجمتها مباشرةً إلى كود. الخطوة التالية: تنفيذ UserDataRegistry، UserDataModule Protocol، تسجيل الأوامر المحجوزة، والـ handlers — متى أعطيت الضوء الأخضر.

انا:
قبل التنفيذ أعتمد الاتجاه، لكن أريد تثبيت بعض التفاصيل المعمارية الأخيرة داخل ADRs أو Design Notes قبل كتابة الكود.

أولاً — UserDataRegistry:

لا أريد أن يكون Registry مجرد قائمة Modules.

يجب أن يكون هو المصدر الوحيد للحقيقة بالنسبة إلى:

/mydata
/forgetme
أي API مستقبلية مرتبطة بدورة حياة User Data
أي Module يملك User Data ولا يوجد في Registry يجب اعتباره خطأ تصميمياً داخل Titan.

أريد أيضاً أن يكون هناك مفهوم واضح للهوية:

UserDataModule يجب أن يعلن:

اسم المكوّن
نوع البيانات التي يديرها
data_for(user_id)
erase(user_id)
حتى لا يصبح التقرير مجرد dict مجهول بعد سنة.

ثانياً — ضمان /forgetme:

أريد تثبيت نقطة مهمة:

/forgetme ليس "محاولة حذف".

هو عقد نهائي:

عند اكتماله يجب أن تكون Titan نفسها غير قادرة على إعادة معرفة البيانات التي حُذفت من خلال User Data Modules المسجلة.

لذلك:

لا cache داخلي يبقي نسخة
لا index داخلي يبقي reference قابل للاسترجاع
لا event قبل المحو يسمح لأي Module بنسخ البيانات
لا إمكانية للمطور لإلغاء العملية عبر hook
بعد erase: فقط completion notification.

ثالثاً — /mydata:

أريد التفريق بين:

الحقيقة الداخلية: ما تعرفه Titan فعلاً عن المستخدم.

العرض: كيف يختار المطور تقديم هذه المعلومات.

الـ hook يغيّر العرض فقط.

مثلاً: يمكنه تحويل JSON إلى نص جميل أو جدول.

لكن لا يستطيع:

حذف Module
حذف حقل
إخفاء وجود تخزين معين
إذا كان يريد عدم جمع معلومة أصلاً فهذا قرار قبل التخزين، وليس بعده.

رابعاً — مراجعة "كل شيء يعرفه المطور":

عندما نقول /mydata يعرض كل شيء، المقصود:

كل ما يدخل ضمن نطاق Titan User Data Contract.

ليس:

قاعدة بيانات المطور الخاصة خارج Titan
Telegram نفسها
أي شيء يخزنه المطور بعيداً عن Registry
لكن داخل Titan يجب ألا توجد منطقة مجهولة.

خامساً — أريد إضافة اختبار معماري قبل التنفيذ:

يجب كتابة حالات فشل متوقعة:

مطور يحاول تسجيل /mydata يدوياً: النتيجة يجب أن تكون رفضاً واضحاً.

Module يعلن User Data لكنه لا يملك erase(): يُرفض عند التسجيل.

Hook يحاول تعديل report: يفشل.

Module يحاول تخزين User Data بدون إعلان: بالنسبة لمكونات Titan الرسمية يجب أن يكون مستحيلاً بالتصميم.

/forgetme يعمل: كل registered modules تستلم erase.

هذه الاختبارات أهم من الكود نفسه لأنها تثبت أن العقد حقيقي.

بعد تثبيت هذه النقاط ابدأ التنفيذ.

Agent:
Finalizing architectural details
خمسة نقاط — أُعالجها بتوازٍ: تحديثان في ADR-016/017 وملف مستقل لحالات الفشل المتوقعة.]
You've reached your monthly free quota limit. 