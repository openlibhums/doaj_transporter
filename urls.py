from django.conf.urls import url

from plugins.doaj_transporter import views

urlpatterns = [
    url(r'^$', views.index, name='doaj_index'),
    url(r'^configure$', views.configure, name='doaj_configure'),
    url(r'issue/(?P<issue_id>\d+)$', views.list_issue, name="doaj_list_issue"),
    url(r'^push/issue$', views.push_issue, name='doaj_push_issue'),
    url(r'^push/article$', views.push_article, name='doaj_push_article'),
]
