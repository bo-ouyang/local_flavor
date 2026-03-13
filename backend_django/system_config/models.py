from django.db import models


class SystemOption(models.Model):
    type = models.CharField(max_length=32, db_index=True)
    value = models.CharField(max_length=32)
    label = models.CharField(max_length=64)
    sort_order = models.IntegerField(default=0)

    class Meta:
        db_table = "system_options"
        indexes = [
            models.Index(fields=["type", "sort_order"]),
            models.Index(fields=["type", "value"]),
        ]
