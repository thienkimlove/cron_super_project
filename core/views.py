import time

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO
from django.core import management
from django.http import StreamingHttpResponse
from django.core.management.commands import loaddata
from core.management.commands import *
from core.models import *
from project.settings import LOG_FILE, LOG_CRON_DIRECTORY


def command_response(site, network_id):
    out = StringIO()
    management.call_command('test_cron', '--network_id=%s' % network_id, '--site=%s' % site,  stdout=out)
    value = out.getvalue()
    yield value

def stream_response_generator():
    for x in range(1,11):
        yield "%s\n" % x  # Returns a chunk of the response to the browser
        time.sleep(1)


def stream_response(request):
    return StreamingHttpResponse(stream_response_generator())



def cron_task(request):
    site = request.GET.get('site', None)
    network_id = request.GET.get('network_id', None)

    if site is not None and network_id is not None:
        resp = StreamingHttpResponse( command_response(site, network_id), content_type='text/html')
        return resp
