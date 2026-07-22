"""
titan.privacy.registry

UserDataRegistry — المصدر الوحيد للحقيقة بالنسبة إلى User Data في Titan.

أي API في Titan تتعلق بدورة حياة User Data تمر عبر هذا الـ Registry.

ADR-016: User Data Registry & erase_user Architecture
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from titan.errors import TitanError

if TYPE_CHECKING:
    from titan.privacy.protocol import UserDataModule


class UserDataRegistry:
    """
    يجمع كل UserDataModule المسجَّل ويُمثّل المصدر الوحيد للحقيقة.

    erase_user() → يُوزَّع على كل module مُسجَّل.
    data_held_for() → يُجمَّع من كل module مُسجَّل.

    Module يملك User Data ولا يوجد هنا يُعدّ خطأ تصميمياً داخل Titan.
    """

    def __init__(self) -> None:
        self._modules: list[UserDataModule] = []

    # -------------------------
    # Registration
    # -------------------------

    def register(self, module: object) -> None:
        """
        تسجيل module في الـ registry.

        يتحقق في مرحلة التهيئة من أن module يُعلن:
            - component_name (str property)
            - data_description (str property)
            - data_for() (async callable)
            - erase()     (async callable)

        Module ناقص يرفع TitanError فورياً — لا تسجيل صامت.
        """
        self._validate(module)
        # Safe cast — validated above
        from titan.privacy.protocol import UserDataModule as _Protocol
        self._modules.append(module)  # type: ignore[arg-type]

    def _validate(self, module: object) -> None:
        missing: list[str] = []

        if not isinstance(getattr(module, "component_name", None), str):
            missing.append("component_name (str property)")
        if not isinstance(getattr(module, "data_description", None), str):
            missing.append("data_description (str property)")
        if not callable(getattr(module, "data_for", None)):
            missing.append("data_for() (async method)")
        if not callable(getattr(module, "erase", None)):
            missing.append("erase() (async method)")

        if missing:
            cls_name = type(module).__name__
            raise TitanError(
                f"UserDataModule registration failed for '{cls_name}': "
                f"missing {', '.join(missing)}. "
                "Every module that holds User Data must declare component_name, "
                "data_description, data_for(), and erase(). "
                "See ADR-016 for the full contract."
            )

    # -------------------------
    # Public API
    # -------------------------

    async def erase_user(self, user_id: int) -> None:
        """
        محو حقيقي لكل User Data مُسجَّلة لهذا المستخدم.

        يُوزَّع على كل module بالترتيب — **يُكمل حتى مع فشل أحدها**.
        لا يستطيع module واحد أن يمنع حذف بيانات بقية الـ modules.

        إذا فشل واحد أو أكثر: يُجمَّع الخطأ ويُرفع بعد اكتمال الجميع.
        إذا نجح الجميع: لا exception.

        هذا عقد نهائي — لا cache، لا index يبقي reference.
        """
        errors: list[tuple[str, Exception]] = []

        for module in self._modules:
            try:
                await module.erase(user_id)
            except Exception as exc:
                errors.append((module.component_name, exc))

        if errors:
            failed = ", ".join(f"'{name}'" for name, _ in errors)
            details = "; ".join(
                f"{name}: {type(exc).__name__}({exc})"
                for name, exc in errors
            )
            raise TitanError(
                f"erase_user() completed with errors in {failed}. "
                f"All other modules were erased successfully. "
                f"Details: {details}"
            )

    async def data_held_for(self, user_id: int) -> dict:
        """
        يجمع ما تعرفه Titan عن هذا المستخدم من كل module مُسجَّل.

        المُعاد dict مفاتيحه component_name لكل module:
            {
                "pending_asks": {
                    "description": "Unfinished interactions waiting for user reply",
                    "count": 1
                },
                ...
            }

        هذا التقرير يُمرَّر لـ /mydata مجمَّداً (MappingProxyType) —
        المطوّر يُنسّق الشكل، لا يغيّر المحتوى.
        """
        result: dict = {}
        for module in self._modules:
            data = await module.data_for(user_id)
            result[module.component_name] = {
                "description": module.data_description,
                **data,
            }
        return result

    # -------------------------
    # Introspection
    # -------------------------

    @property
    def module_names(self) -> tuple[str, ...]:
        """أسماء المكوّنات المُسجَّلة — للـ inspection والاختبار."""
        return tuple(m.component_name for m in self._modules)

    def __len__(self) -> int:
        return len(self._modules)
