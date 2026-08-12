"""
titan.lifecycle

طبقة إدارة دورة حياة تشغيل البوت — داخلية بالكامل.

ADR-019: Lifecycle Management Layer

المحتويات:
  runner.py  — PollingRunner: حلقة polling وبروتوكول الإغلاق.
  signals.py — install / uninstall: إشارات SIGTERM / SIGINT.

لا يُصدَّر شيء من هذا المجلد خارج titan.bot.
"""
