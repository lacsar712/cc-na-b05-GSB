from django.db import models, transaction

DEFAULT_LIMIT = 2000.0


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


class CandelaLimit(models.Model):
    """全台唯一的坎德拉上限，只有一行（id 固定为 1）。"""

    value = models.FloatField("光强上限（坎德拉）")
    updated_by = models.CharField("最后修改人", max_length=64)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = verbose_name_plural = "坎德拉上限"

    def __str__(self):
        return f"{self.value}"

    @classmethod
    def current(cls) -> "CandelaLimit":
        obj, _ = cls.objects.get_or_create(
            pk=1, defaults={"value": DEFAULT_LIMIT, "updated_by": "system"}
        )
        return obj

    @classmethod
    @transaction.atomic
    def change(cls, new_value: float, operator: str) -> "CandelaLimit":
        """修改上限并同步写入一条履历；履历里的旧值不会被以后的改动覆盖。"""
        obj = cls.objects.select_for_update().get(pk=1)
        old_value = obj.value
        LimitHistory.objects.create(
            old_value=old_value,
            new_value=new_value,
            operator=operator,
        )
        obj.value = new_value
        obj.updated_by = operator
        obj.save()
        return obj


class LimitHistory(models.Model):
    """上限每次改动一条，记录旧值、新值与操作者。"""

    old_value = models.FloatField("旧上限")
    new_value = models.FloatField("新上限")
    operator = models.CharField("操作者", max_length=64)
    created_at = models.DateTimeField("修改时刻", auto_now_add=True)

    class Meta:
        ordering = ["-id"]
        verbose_name = verbose_name_plural = "上限变更履历"


class RejectedLight(models.Model):
    """超过上限的填写被拒绝后留档；limit_at_rejection 是拒绝当时的上限快照。"""

    aid_code = models.CharField("灯号", max_length=40)
    measured_cd = models.FloatField("所填亮度")
    limit_at_rejection = models.FloatField("当时上限")
    rejected_by = models.CharField("填写人", max_length=64)
    rejected_at = models.DateTimeField("拒绝时刻", auto_now_add=True)

    class Meta:
        ordering = ["-id"]
        verbose_name = verbose_name_plural = "被拒灯光"
