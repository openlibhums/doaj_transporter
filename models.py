from django.db import models
from django.utils import timezone


class DOAJArticle(models.Model):
    article = models.OneToOneField("submission.Article")
    doaj_id = models.CharField(max_length=255)
    exported = models.DateTimeField(blank=True, null=True)
    last_updated = models.DateTimeField(blank=True, null=True)

    class Meta:
        unique_together = ("article", "doaj_id")

