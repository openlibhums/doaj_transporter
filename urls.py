from django.conf.urls import url

from plugins.doaj import views

urlpatterns = [
    url(r'^$', views.index, name='doaj_index'),
]
