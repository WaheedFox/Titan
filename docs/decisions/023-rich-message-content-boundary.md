# 023 — Rich Message Content Boundary

**Status:** Accepted  
**يعتمد على:** ADR-004 — Error Contracts  
**يعتمد على:** ADR-008 — Message Links Protocol  

---

## Proposal

إضافة دعم رسمي لـ Telegram Rich Messages في Titan من خلال قيمة outgoing
صغيرة ومحددة باسم `RichContent`، مع الحفاظ على أفعال `Context` الحالية:

```python
await ctx.send("hello")
await ctx.send(text="hello")
await ctx.send(RichContent.html("<b>hello</b>"))
```

الهدف ليس نسخ Telegram داخل Titan، ولا بناء document model كامل. الهدف هو
إضافة حد دلالي واضح بين content الذي ينشئه المطور وTelegram payload الذي
ينقله adapter.

---

## Investigation

التحقيق الكامل موجود في:

→ [`docs/internal/investigations/rich-messages.md`](../internal/investigations/rich-messages.md)

مرّ التصميم بمرحلتين من المراجعة العدائية. النتيجة المهمة ليست أن الفرضية
الأولى صمدت، بل أنها تغيرت:

```text
RichMessageInput       → RichContent
constructor snapshot   → serialization-boundary snapshot
ctx.send_rich()        → existing Context verbs + typed value
```

### ما ثبت

- `text` هو اسم parameter الحالي في `Context.send()`, `reply()`, و`edit()`.
  تغيير الاسم إلى `content` يكسر الاستدعاءات العامة التي تستخدم `text=`.
- raw dict لا يملك mode invariant أو type distinction أو dispatch contract.
- shallow copy لا يحمي nested containers.
- `deepcopy` قد ينسخ opaque media/file objects ويكسر هويتها.
- public freeze يحتاج serializer خاصاً ولا ينتج JSON payload مباشرةً.
- drafts وstreaming يملكان lifecycle مختلفاً، ولا ينبغي إدخالهما في basic
  send/reply/edit.
- annotation الحالية لـ `text` هي `str`، لكن التنفيذ الحالي لا يرفض `None`
  محلياً؛ يمرره إلى `Telegram.send_message()`. لا يوجد معنى موثَّق لـ
  `None` في `send/reply/edit`، لذلك قبول runtime الحالي incidental behavior
  وليس compatibility contract مثبتاً.

### السؤال الذي حُسم

السؤال ليس: “هل ننسخ عند إنشاء `RichContent`؟”

السؤال الصحيح: “متى يصبح الطلب مستقلاً عن input object؟”

الإجابة هي serialization boundary الخاصة بعملية الإرسال. قبلها يستطيع
المطور بناء المحتوى وتعديله. بعدها لا تعتمد العملية على mutation لاحقة.

---

## Decision

### 1. `RichContent` — outgoing tagged value صغيرة

`RichContent` قيمة public تمثل **وضعاً واحداً** من outgoing rich content:

```python
from titan import RichContent

RichContent.html(markup)
RichContent.markdown(markup)
RichContent.blocks(blocks)
```

الـ modes mutually exclusive بطبيعتها. لا يوجد constructor public عام يقبل
payload غير محدد، ولا يمكن إنشاء قيمة بلا mode أو بأكثر من mode.

`RichContent`:

- لا تجلب ولا ترسل ولا تعدل الرسائل.
- لا تفسر HTML أو Markdown.
- لا تحول mode إلى mode آخر.
- لا تعرف identity أو archive أو draft lifecycle.
- تملك representation وvalidation invariants الخاصة بالـ mode الذي أُنشئت به.
- Titan request boundary تملك serialization إلى transport-content snapshot
  مستقل عن input graph.

تُصدَّر `RichContent` من جذر الحزمة لأنها جزء مطلوب من الاستخدام العام
المباشر، مثل `InlineKeyboard`. لا تُصدَّر classes لكل نوع block أو media أو
button.

### 2. modes صريحة، بلا parser أو projection

كل constructor يختار transport mode صراحةً:

```text
RichContent.html(markup)     → html mode
RichContent.markdown(markup) → markdown mode
RichContent.blocks(blocks)   → blocks mode
```

لا يحاول Titan:

- تخمين mode من string.
- تحويل HTML إلى Markdown أو العكس.
- إنشاء canonical AST.
- اختراع `text` projection لمحتوى Rich.
- دمج `RichContent` مع `RichMessage` الواردة.

`text` يبقى اختيارياً على `Message`. وجود Rich content لا يفرض اختراع نص
بديل له.

### 3. `blocks` boundary خفيفة

`RichContent.blocks()` تقبل ordered block mappings داخل boundary Titan، دون
تحويلها إلى نموذج Telegram كامل:

```python
RichContent.blocks([
    {
        "type": "paragraph",
        "text": "Hello",
        "future_field": {"enabled": True},
    }
])
```

Titan تضمن أن القيمة blocks وليست html أو markdown، وأن الحاوية الأساسية
صحيحة. أما schema التفصيلية للـ block وأنواعها وحقول Telegram المستقبلية
فتبقى في boundary النقل. لا `RichBlock` ولا `RichHeading` ولا mirror كامل
لـ Telegram في Core.

الـ unknown fields داخل block mapping لا تُحذف لمجرد أنها غير معروفة لـ
Titan. إذا رفضتها Telegram، فهذا Telegram-level failure.

#### الحد الأدنى الدقيق لـ `blocks`

`blocks` هو **ordered `Sequence` of mappings**:

```python
RichContent.blocks([])                         # صالح من ناحية Titan shape
RichContent.blocks([{}])                       # صالح من ناحية Titan shape
RichContent.blocks([{"foo": "bar"}])           # صالح؛ Telegram قد ترفضه
RichContent.blocks({"type": "paragraph"})      # مرفوض محلياً
RichContent.blocks(({"type": "p"},))           # صالح
RichContent.blocks(iter([{"type": "p"}]))      # مرفوض؛ ليس sequence ثابتاً
```

بالتحديد:

- sequence تقبل `list` و`tuple` وما يحقق `Sequence`، مع استبعاد `str` و
  `bytes` وmapping المفرد وone-shot iterator.
- كل عنصر يجب أن يكون `Mapping`؛ لا يُشترط وجود `type` أو أي field Telegram
  آخر.
- empty sequence وempty mapping لا يخالفان Titan shape. صلاحية الرسالة
  النهائية أو grammar الـ block مسؤولية Telegram.
- unknown fields داخل block mapping لا تُحذف ولا تُعاد تسميتها.
- nested mappings/lists داخل block تتبع نفس serialization boundary.

هذا هو الحد الأدنى المقصود بـ “basic shape”: Titan تملك container/order/type
distinction فقط، ولا تملك block grammar. كلمة `Sequence` هنا تعني input
محدداً يمكن للـ request boundary materializeه، وليست streaming iterator.

### 4. Context API: existing verbs مع union يحافظ على `text=`

تُوسَّع أنواع المعامل الحالي دون تغيير اسمه أو إضافة أفعال موازية:

```python
ctx.send(
    text: str | RichContent,
    parse_mode: str | None = None,
    reply_markup: Any | None = None,
)

ctx.reply(
    text: str | RichContent,
    parse_mode: str | None = None,
    reply_markup: Any | None = None,
)

ctx.edit(
    text: str | RichContent,
    parse_mode: str | None = None,
    reply_markup: Any | None = None,
)
```

القواعد:

- `str` يذهب إلى text transport الحالي.
- `RichContent` يذهب إلى rich transport بحسب mode.
- positional Rich usage مدعوم وواضح:
  `ctx.send(RichContent.html(...))`.
- `text=RichContent.html(...)` يظل صحيحاً من ناحية backward-compatible
  binding، رغم أن positional usage أوضح.
- لا يُضاف `content=` إلى هذه الأفعال.
- لا تُضاف `send_rich()`, `reply_rich()`, أو `edit_rich()`.
- raw `dict` ليس implicit Rich input، ويُرفض كـ Titan contract violation.
- `parse_mode` مع `RichContent` تعارض في نية Titan: الـ constructor اختار
  mode بالفعل، لذلك يُرفض قبل Telegram حتى لو كان Telegram يستطيع قبول
  parameter إضافياً في بعض endpoints.
- `reply_markup` سطح مستقل؛ Rich content لا يجعل keyboard جزءاً من
  `RichContent`.
- `None` ليس outgoing content صالحاً لهذه الأفعال. لا يُضاف إلى union لمجرد
  أن Python runtime الحالية تمرره إلى Telegram.

`ctx.edit()` تبقى callback-only وفق contract الحالي. تغيير قيمة المحتوى لا
يغير نطاق edit أو identity behavior.

#### `text=None` — compatibility verification

**FACT:** المصدر الحالي يعلن `text: str`، و`Telegram.send_message()` يبني
payload يحتوي `"text": text` دون guard محلي لـ `None`. لذلك:

```python
ctx.send(text=None)
```

يمكنه الوصول إلى Telegram إذا كان `chat_id` موجوداً، لكن لا توجد له دلالة
Titan موثَّقة ولا مسار نجاح مقصود.

**DECISION:** ADR-023 لا يعتبر هذا القبول incidental behavior جزءاً من
backward compatibility. `None` يبقى invalid input مستقبلاً، ويجب أن يُرفض
كـ `TitanError` قبل أي serialization أو network. صياغة Contract Delta يجب أن
تذكر صراحةً أن compatibility محفوظة للقيم المدعومة `str`، لا لكل object يقبله
runtime غياباً للتحقق.

### 5. Serialization boundary — ضمان السلوك

في basic `send`, `reply`, و`edit`، تمر العملية بالمراحل المنطقية التالية:

```text
RichContent input
    → Titan validation
    → transport-content serialization boundary
    → immutable content snapshot
    → adapter maps snapshot to Telegram request
    → network await
```

الضمان المعماري هو:

> بعد عبور `RichContent` إلى serialization boundary، لا تعتمد عملية الإرسال
> على mutation لاحقة للـ input object.

يعني ذلك:

1. mutation قبل boundary يمكن أن تظهر في payload؛ هذا يسمح ببناء المحتوى
   تدريجياً قبل الإرسال.
2. عند boundary تُحوَّل nested mappings/lists إلى containers مستقلة عن input
   أو إلى تمثيل مكافئ يضمن ذلك.
3. opaque leaves لا تُنسخ بـ `deepcopy`. إذا كانت مدعومة، يستهلكها serializer
   المعتمد إلى transport-compatible representation قبل إنشاء snapshot؛ إذا
   تعذر ذلك، يرفع Titan خطأً قبل network.
4. بعد إنشاء content snapshot لا تُقرأ containers أو opaque objects الأصلية
   مرة أخرى في عملية الإرسال.
5. adapter يقرأ snapshot فقط، ويحوّله إلى method/body خاص بـ Telegram.
6. أول network await يحدث بعد تثبيت content snapshot وrequest data اللازم.
7. mutation لاحقة للـ input object لا تؤثر على الطلب الجاري.

`transport-content serialization boundary` هي boundary منطقية لا اسم public
method. نهايتها هي content snapshot الذي لا يعتمد على input graph. لا تعني
`RichContent.to_dict()` بالضرورة Telegram-ready request، ولا تنقل ملكية
Telegram endpoint إلى Core:

```text
Titan:
    mode validation + container/leaf snapshot

Adapter:
    snapshot → Telegram method/body

Telegram:
    remote validation, permissions, network
```

هذا القرار يثبت **الضمان** ولا يفرض خوارزمية copy بعينها. reference حي
حتى نهاية network مرفوض؛ constructor deep copy لكل object غير مطلوب.

الدعم المستقبلي لـ drafts أو queues يجب أن يأخذ snapshot عند enqueue أو
session transition الخاص به. لا يستعير هذا القرار semantics غير موجودة في
basic operations.

### 6. Incoming `Message.rich_message`

الجهة الواردة مستقلة:

```python
message.rich_message: RichMessage | None
```

`RichMessage` read model data-only، يعرض ما وصل من Telegram. لا يتحول تلقائياً
إلى `RichContent`، ولا يُقبل مكانه في outgoing Context methods بلا تحويل
صريح من المطور.

القواعد الواردة:

- `Message.text` يمكن أن يكون `None`.
- لا يُنشأ update route جديد لـ Rich Messages.
- الرسالة Rich تدخل message route الحالي.
- `Message.raw` و`Message.to_dict()` يحتفظان بعلاقتهما الحالية بالـ raw
  Telegram payload.
- لا parser عام يحوّل incoming markup إلى AST أو RichContent.

#### Minimum `RichMessage` read-model contract

`RichMessage` ليس outgoing builder ولا Telegram schema mirror. هو data-only
read model يملك الحد الأدنى التالي:

```python
message.rich_message: RichMessage | None

rich.mode       # str | None — mode المعروف إذا كان واضحاً
rich.raw        # raw rich representation كما وصلت
rich.to_dict()  # نفس representation، مع unknown fields
```

والضمانات:

- يحتفظ بالـ raw block mappings، بما فيها nested mappings وunknown fields؛
  لا يعيد بناءها إلى `RichBlock` objects.
- يحتفظ بالـ mode إذا كان incoming representation يعلنه أو يمكن تحديده
  بلا تخمين. mode غير المعروف لا يُحوَّل إلى mode معروف.
- `to_dict()` يعيد representation الواردة التي يملكها النموذج، لا
  outgoing envelope ولا text projection.
- لا يملك methods للإرسال أو التعديل أو التحويل.
- لا يملك mutation API ولا snapshot promise مستقلاً عن contract الحالي
  لـ `Message.raw`: هو data-only view، وraw Telegram mapping تبقى raw
  representation وليست public immutable value.
- إذا احتوت Telegram representation على fields لا يفهمها Titan، تبقى في
  `raw` ولا تمنع إنشاء read model.

لذلك `RichMessage` أضيق من `RichContent`: الأولى تصف data وصلت، والثانية
تفرض input mode وserialization boundary قبل الإرسال. لا يوجد constructor
عام يحوّل `RichMessage` إلى `RichContent` تلقائياً.

### 7. Errors — Titan boundary مقابل Telegram semantics

وفق ADR-004:

**TitanError** عندما تكون المشكلة في عقد Titan:

- raw dict استُخدم كـ implicit Rich content.
- mode غير صالح أو أكثر من mode.
- blocks ليست في الشكل الأساسي المقبول.
- `parse_mode` استُخدم مع RichContent.
- Context state غير صالح، مثل edit خارج callback context.
- opaque leaf لا يملك serialization contract قابلاً للاستخدام.

**TelegramError** عندما تكون المشكلة بعد إرسال payload إلى Telegram أو في
network:

- Telegram ترفض HTML أو Markdown grammar.
- Telegram ترفض field combination.
- Telegram تفشل في media resolution أو upload.
- chat أو account permissions تمنع العملية.

Titan لا تعيد تصنيف كل خطأ Telegram إلى classes جديدة، ولا تتحقق من كامل
Telegram schema داخل Core لمجرد أن blocks مرّت عبرها.

### 8. Message Links وArchive

هذا القرار لا يغير Message Links Protocol:

- الإرسال عبر `ctx.send()` أو `ctx.reply()` يمر بمسار Context المعتاد، ولذلك
  يحافظ على identity registration.
- الإرسال المباشر عبر `bot.telegram` يبقى direct transport ولا يسجل identity
  تلقائياً.
- `edit()` لا ينشئ identity جديدة.
- Archive لا يحصل على وعد Rich replay في v1.
- `text=None` يظل تمثيلاً مقبولاً للرسالة التي لا تملك text projection.

### 9. خارج النطاق

لا يشمل هذا القرار:

- drafts أو streaming أو cancellation lifecycle.
- Rich buttons كـ `InlineKeyboard` abstraction.
- parser أو renderer أو canonical AST.
- full Telegram schema mirror في Core.
- fallback صامت إلى `sendMessage`.
- تغيير `CONTRACT.md` أو implementation details؛ تلك هي الخطوة التالية
  بعد تسجيل القرار.

---

## Rule

**المحتوى يُمثَّل typed عند الحد الذي يملك semantics، ويُترك transport
schema عند الحد الذي يملكه transport.**

في Rich Messages يعني ذلك:

- `RichContent` يملك mode، الاتجاه outgoing، والتحقق الذي يخص Titan.
- `RichContent` يملك content representation وvalidation invariants؛ لا يملك
  public serialization API.
- `RichMessage` يملك representation الواردة.
- `Context` يملك دورة request الحالية.
- request boundary تملك serialization إلى owned transport-content snapshot.
- adapter يملك تحويل mode إلى Telegram API.
- serialization boundary تثبت request قبل network.

لا تُضاف class أو method لأن شكلها أجمل. تُضاف فقط إذا كانت تملك invariant
أو boundary لا يستطيع dict أو transport وحده امتلاكها بوضوح.

---

## Alternatives Considered

### Raw `rich_message=` dictionary

```python
ctx.send(rich_message={"html": "<b>hello</b>"})
```

أقل surface في البداية، لكنه يضع mode validation وmutual exclusion وdispatch
في كل caller أو في conditional كبير داخل Context. كما أنه لا يميز Rich input
عن arbitrary dict ولا يوفر type contract قابلاً للاكتشاف.

**رُفض:** أقل code ليس أقل تعقيداً إذا انتقل التعقيد إلى كل استخدام.

### `ctx.send_rich()` ورفاقها

تجعل intent ظاهراً، لكنها تضيف ثلاثة أفعال لكل lifecycle وتكرر قواعد
Context. هذا يخالف Alias Consistency Rule في CONTRACT عندما لا تكون هناك
دلالة تشغيلية مختلفة.

**رُفض:** Rich content اختلاف في نوع القيمة، لا عملية Context جديدة.

### تغيير parameter إلى `content`

أوضح لغوياً، لكنه يكسر `ctx.send(text="hello")` و`reply(text=...)` و
`edit(text=...)` الحالية.

**رُفض:** الوضوح الاسمي لا يبرر breaking change في v1.

### `text=` و`content=` معاً

يبدو أنه يحل readability وcompatibility في آن واحد، لكنه يخلق حالات:

```python
ctx.send(text="a", content=RichContent.html("b"))
ctx.send(text=None, content=None)
```

ويحتاج قواعد precedence أو error إضافية لا توجد في API الحالية.

**رُفض:** يوسّع surface ويضيف invalid states.

### `deepcopy` أو recursive freeze عند الإنشاء

كلاهما يعطي إحساساً بقيمة immutable، لكن `deepcopy` قد ينسخ objects لا
يملك Titan معناها، وfreeze يحتاج conversion عند serialization. كما أنهما
يفرضان semantics قبل أن يبدأ الإرسال.

**رُفض:** الضمان المطلوب يخص payload بعد boundary، لا كل object graph عند
constructor.

### نموذج Telegram كامل داخل Core

`RichBlock`, `RichMedia`, `RichButton`, `RichHeading` وغيرها قد تبدو typed،
لكنها تنقل ملكية Telegram schema إلى Titan وتزيد تكلفة التغيير.

**رُفض:** blocks تبقى mappings داخل boundary خفيفة حتى يظهر مستهلك حقيقي
يبرر model أكثر تحديداً.

### قبول `RichMessage` نفسها للإرسال

يقلل نوعاً واحداً، لكنه يخلط incoming read model مع outgoing input value،
ويجعل اتجاه البيانات غير واضح.

**رُفض:** اختلاف الاتجاه والـ lifecycle يستحقان نوعين مختلفين.

---

## Consequences

### المكتسب

- API basic صغيرة: ثلاثة constructors وثلاثة Context verbs موجودة أصلاً.
- استدعاءات `text=` الحالية تبقى صالحة.
- Rich dispatch صريح type-wise، بلا dict key heuristics.
- nested request payload يصبح مستقلاً بعد serialization boundary.
- opaque media objects لا تُنسخ عشوائياً.
- incoming وoutgoing وediting وidentity تبقى حدوداً منفصلة.
- Core لا يتحول إلى Telegram 2.

### القيود المقبولة

- اسم parameter `text` يقبل `RichContent` إلى جانب `str` للحفاظ على
  compatibility مع `text=`.
- `text=None` غير مدعوم رغم أن runtime الحالي يمرره إلى Telegram؛ هذا
  incidental acceptance لا يصبح contract.
- المطور يحتاج اختيار mode صريح؛ لا conversion تلقائي.
- blocks تضمن ordered sequence of mappings فقط؛ empty/unknown block shape
  يمر إلى Telegram.
- `RichMessage` يبقى raw-backed read model، لا immutable snapshot جديداً.
- Rich archive replay غير مضمون في v1.
- draft/streaming APIs ستحتاج قرار lifecycle مستقلاً.
- opaque leaves تحتاج serialization contract خاصاً بها؛ لا يمكن لـ Titan
  تخمين معنى object لمجرد أنه قابل للنسخ.

### ترتيب ما بعد ADR

1. تحديث `CONTRACT.md` بصياغة الضمانات العامة، خصوصاً parameter union
   وserialization boundary.
2. تنفيذ `RichContent` و`RichMessage` وفق هذا القرار.
3. تنفيذ adapter serialization.
4. كتابة tests للـ modes، signatures، mutation boundary، errors، incoming،
   editing، وidentity.

لا يغيّر هذا ADR أي ملف من `src/titan/` أو `tests/` بنفسه.