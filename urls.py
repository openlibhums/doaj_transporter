from django.conf.urls import url

from plugins.doaj_transporter import views

urlpatterns = [
    url(r'^$', views.index, name='doaj_index'),
    url(r'^configure$', views.configure, name='doaj_configure'),
]
