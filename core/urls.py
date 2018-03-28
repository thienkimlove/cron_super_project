from django.conf.urls import url

from core.views import *

app_name = "core"


urlpatterns = [
    url(r'^cron/$', cron_task, name='cron_tab'),
    url(r'^test_stream/$', stream_response, name='test_stream'),

]