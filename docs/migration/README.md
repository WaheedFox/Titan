# الانتقال إلى Titan

هذه الأدلة مكتوبة للمطورين القادمين من إطار Telegram آخر.

كل دليل يشرح **الفلسفة** أولاً، ثم المقابلات، ثم نقاط الاحتكاك غير الواضحة.

---

## اختر إطارك

| الإطار الحالي | الدليل |
|---|---|
| **python-telegram-bot (PTB)** | [from-ptb.md](from-ptb.md) |
| **aiogram** | [from-aiogram.md](from-aiogram.md) |
| **pyTelegramBotAPI (telebot)** | [from-telebot.md](from-telebot.md) |

---

## ماذا ستجد في كل دليل

1. **الفرق الفلسفي** — لماذا Titan يعمل بطريقة مختلفة، وليس فقط كيف.
2. **خريطة المقابلات** — هذا المفهوم في إطارك = هذا في Titan.
3. **الأشياء التي ستنكسر** — نقاط الاحتكاك غير الواضحة التي تستغرق وقتاً للاكتشاف.
4. **الأشياء التي لا يوجد لها مقابل مباشر** — تحتاج إعادة تصميم، لا مجرد ترجمة syntax.

---

## للأدوات — Migration Knowledge API

إذا كنت تبني أداة أو تريد الاستعلام عن المعرفة برمجياً:

```python
from titan.migration import frameworks, concepts, compare

frameworks()            # ["aiogram", "ptb", "telebot"]
concepts("aiogram")     # ["callback", "command", "context", ...]
compare("aiogram", "middleware")   # ConceptMapping(...)
```
