from django.contrib import admin

from plugins.doaj_transporter.models import DOAJDeposit


class DOAJDepositAdmin(admin.ModelAdmin):
    """Displays objects in the Django admin interface."""
    list_display = ('id', 'article', 'identifier', 'success')
    list_filter = ('article', 'article__journal', 'success')
    search_fields = ('identifier', 'article__title')


admin_list = [
    (DOAJDeposit, DOAJDepositAdmin),
]

[admin.site.register(*t) for t in admin_list]
