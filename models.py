from django.db import models
from django.utils import timezone


class DOAJArticle(models.Model):
    article = models.OneToOneField("submission.Article")
    doaj_id = models.CharField(max_length=255)
    exported = models.DateTimeField(default=timezone.now)
    last_updated = models.DateTimeField(default=timezone.now)

