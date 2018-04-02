from django.conf.urls import url

from core.views import *

app_name = "core"


urlpatterns = [
    url(r'^cron/$', cron_task, name='cron_tab'),
    url(r'^quan_cron/$', cron_test_task, name='cron_test_tab'),
    url(r'^test_stream/$', stream_response, name='test_stream'),
    url(r'^ajax_cron/(?P<site>[\w-]+)/(?P<network_id>[\w-]+)$', ajax_cron, name='ajax_cron'),

]