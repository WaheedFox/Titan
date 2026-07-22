"""
titan.privacy.protocol

UserDataModule — العقد الذي يُطبّقه كل module يخزّن User Data داخل Titan.

ADR-016: User Data Registry & erase_user Architecture
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class UserDataModule(Protocol):
    """
    عقد كل module يخزّن User Data داخل Titan.

    Module يُطبّق هذا العقد يُعلن:
        - من هو (component_name)
        - ماذا يخزّن (data_description)
        - كيف يُعرض ما يعرفه (data_for)
        - كيف يُمحى ما يعرفه (erase)

    التسجيل يجعل البيانات تظهر تلقائياً في:
        - erase_user()
        - data_held_for()
        - /mydata
        - /forgetme

    Module لا يُطبّق هذا العقد يُرفض عند التسجيل في UserDataRegistry.
    """

    @property
    def component_name(self) -> str:
        """
        اسم المكوّن — ثابت، قابل للقراءة.

        يُستخدم في تقارير /mydata كعنوان للقسم.
        مثال: "pending_asks", "user_preferences"
        """
        ...

    @property
    def data_description(self) -> str:
        """
        وصف موجز لنوع البيانات التي يديرها هذا المكوّن.

        يُعرض في /mydata بجوار البيانات.
        مثال: "Unfinished interactions waiting for user reply"
        """
        ...

    async def data_for(self, user_id: int) -> dict:
        """
        الحقيقة الداخلية: ما تعرفه Titan عن هذا المستخدم.

        المُعاد يجب أن يكون قابلاً للتسلسل (JSON-serializable).
        يُعرض في /mydata — المطوّر يُنسّق الشكل، لا يغيّر المحتوى.
        """
        ...

    async def erase(self, user_id: int) -> None:
        """
        محو حقيقي لكل User Data لهذا المستخدم.

        يجب أن يكون:
        - حذفاً حقيقياً — لا flags، لا soft delete
        - كاملاً — لا بيانات جزئية تبقى
        - نهائياً — لا إمكانية للاسترجاع عبر Titan

        Module لا يُطبّق هذا المتطلب يُرفض عند التسجيل.
        """
        ...
