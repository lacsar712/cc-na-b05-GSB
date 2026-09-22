from django.db import models

DEFAULT_CANDELA_LIMIT = 2000.0


class Inspection(models.Model):
    aid_code = models.CharField("航标编号", max_length=40)
    measured_cd = models.FloatField("实测光强")
    required_cd = models.FloatField("要求光强")
    bearing_error_deg = models.FloatField("方位偏差")
    verdict = models.CharField("结论", max_length=20)
    note = models.CharField("说明", max_length=200)
    created_by = models.CharField("登记人", max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]


class LimitSetting(models.Model):
    """坎德拉上限，单行保存当前生效值。"""

    value = models.FloatField("坎德拉上限")
    updated_by = models.CharField("操作者", max_length=64, default="system")
    updated_at = models.DateTimeField(auto_now=True)

    @classmethod
    def current(cls) -> "LimitSetting":
        obj, _ = cls.objects.get_or_create(
            pk=1, defaults={"value": DEFAULT_CANDELA_LIMIT}
        )
        return obj


class LimitChange(models.Model):
    """上限变更履历：旧值、新值、操作者。"""

    old_value = models.FloatField("旧值")
    new_value = models.FloatField("新值")
    changed_by = models.CharField("操作者", max_length=64)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]


class RejectedReading(models.Model):
    """超上限被拒的填写，当时上限随行快照保存。"""

    aid_code = models.CharField("航标编号", max_length=40)
    measured_cd = models.FloatField("所填亮度")
    limit_at_time = models.FloatField("当时上限")
    submitted_by = models.CharField("提交人", max_length=64)
    rejected_at = models.DateTimeField("拒绝时刻", auto_now_add=True)

    class Meta:
        ordering = ["-id"]
