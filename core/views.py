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
from django.core.cache import cache
import time
import subprocess
import shlex

def follow(filename):
    yield 'Start'
    filename.seek(0,2)
    while True:
        line = filename.readline()
        if not line:
            time.sleep(0.1)
            continue
        yield line
        if 'End' in line:
            break

def stream_response_generator():
    logfile = open("/tmp/store_message/quan_test","r")
    loglines = follow(logfile)
    for line in loglines:
        yield line

def command_response(site, network_id):
    process = subprocess.Popen(["/root/Env/project/bin/python", "/var/www/html/project/manage.py", "test_cron", "--site=%s" % site, "--network_id=%s" % network_id], stdout=subprocess.PIPE)

    while True:
        output = process.stdout.readline().decode()
        if output == '' and process.poll() is not None:
            break
        if output:
            yield output.strip()

def command_response_test(site, network_id):
    process = subprocess.Popen(["/root/Env/project/bin/python", "/var/www/html/project/manage.py", "cache", "--site=%s" % site, "--network_id=%s" % network_id], stdout=subprocess.PIPE)

    while True:
        output = process.stdout.readline().decode()
        if output == '' and process.poll() is not None:
            break
        if output:
            yield output.strip()


def stream_response(request):
    return StreamingHttpResponse(stream_response_generator())

def cron_test_task(request):
    site = request.GET.get('site', None)
    network_id = request.GET.get('network_id', None)

    if site is not None and network_id is not None:
        return StreamingHttpResponse(command_response_test(site, network_id))

def cron_task(request):
    site = request.GET.get('site', None)
    network_id = request.GET.get('network_id', None)

    if site is not None and network_id is not None:
        resp = StreamingHttpResponse( command_response(site, network_id), content_type='text/html')
        return resp
