from django.urls import re_path

from plugins.doaj_transporter import views

urlpatterns = [
    re_path(r'^$', views.index, name='doaj_index'),
    re_path(r'^configure$', views.configure, name='doaj_configure'),
    re_path(r'issue/(?P<issue_id>\d+)$', views.list_issue, name="doaj_list_issue"),
    re_path(r'article/(?P<article_id>\d+)/json$', views.article_json, name="doaj_article_json"),
    re_path(r'^push/issue$', views.push_issue, name='doaj_push_issue'),
    re_path(r'^push/article$', views.push_article, name='doaj_push_article'),
]
