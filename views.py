from django.shortcuts import render, redirect
from django.core.urlresolvers import reverse
from django.core.management import call_command
from django.contrib import messages

from plugins.doaj import plugin_settings, logic
from journal import models

#@has_journal
def index(request):
    issues = models.Issue.objects.filter(journal=request.journal)


    if request.POST:

        if 'export-issue' in request.POST:
            return logic.prepare_export_for_issue(request)

        if 'export-article' in request.POST:
            return logic.prepare_export_for_article(request)

        if 'export-journal' in request.POST:
            pass


        messages.add_message(
            request,
            messages.INFO,
            'Command complete.'
        )

        return redirect(reverse('doaj_index'))

    template = 'doaj/index.html'
    context = {
        'issues': issues,
        'articles': logic.get_articles(request)
    }

    return render(request, template, context)


def settings(request):

    template = 'doaj/settings.html'
    context = {}

    return render(request, template, context)
