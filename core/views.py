import contextlib
import datetime
import socket
import time
import subprocess
import shlex

import os
import pika
import rabbitpy as rabbitpy
from django.http import StreamingHttpResponse, HttpResponse
from django.shortcuts import render


def send_message_to_socket(message):
    host = socket.gethostname()  # as both code is running on same pc
    port = 9999  # socket server port number

    client_socket = socket.socket()  # instantiate
    client_socket.connect((host, port))  # connect to the server

    client_socket.send(message.encode())  # send message
    client_socket.close()  # close the connection


def receive_message():
    host = socket.gethostname()  # as both code is running on same pc
    port = 5000  # socket server port number

    client_socket = socket.socket()  # instantiate
    client_socket.connect((host, port))  # connect to the server

    while True:
        data = client_socket.recv(1024).decode()  # receive response
        if not data:
            time.sleep(0.1)
            continue
        yield data
        if 'Done' in data:
            client_socket.close()  # close the connection
            break


def new_follow(name):
    current = open(name, "r", os.O_NONBLOCK)
    curino = os.fstat(current.fileno()).st_ino
    while True:
        while True:
            line = current.readline()
            if not line:
                break
            yield line

        try:
            if os.stat(name).st_ino != curino:
                new = open(name, "r", os.O_NONBLOCK)
                current.close()
                current = new
                curino = os.fstat(current.fileno()).st_ino
                continue
        except IOError:
            pass
        time.sleep(1)


# Unix, Windows and old Macintosh end-of-line
newlines = ['\n', '\r\n', '\r']

def unbuffered(proc, stream='stdout'):
    stream = getattr(proc, stream)
    with contextlib.closing(stream):
        while True:
            out = []
            last = stream.read(1)
            # Don't loop forever
            if last == '' and proc.poll() is not None:
                break
            while last not in newlines:
                # Don't loop forever
                if last == '' and proc.poll() is not None:
                    break
                out.append(last)
                last = stream.read(1)
            out = ''.join(out)
            yield out


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

    yield 'Start with network_id=%s for site=%s' % (network_id, site)
    yield '<br/>'
    process = subprocess.Popen(["/root/Env/project/bin/python", "/var/www/html/project/manage.py", "test_cron", "--site=%s" % site, "--network_id=%s" % network_id], stdout=subprocess.PIPE, bufsize=1)

    while True:
        output = process.stdout.readline().decode()
        if output == '' and process.poll() is not None:
            break
        if output:
            yield output.strip()

def on_message(channel, method_frame, header_frame, body):

    channel.basic_ack(delivery_tag=method_frame.delivery_tag)
    yield body
    channel.stop_consuming()


def command_response_test(site, network_id):

    connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
    channel = connection.channel()
    channel.basic_consume(on_message, 'pdfprocess')
    channel.start_consuming()
    connection.close()
    yield 'Response'

def stream_response(request):
    return StreamingHttpResponse(stream_response_generator())

def cron_test_task(request):
    site = request.GET.get('site', None)
    network_id = request.GET.get('network_id', None)

    return render(request, 'core/index.html')


def ajax_cron(request, site, network_id):

    routing = '%s%s' % (site, network_id)
    subprocess.call(
        ["/root/Env/project/bin/python", "/var/www/html/project/manage.py", "test_cron", "--site=%s" % site,
         "--network_id=%s" % network_id, "--routing=%s" % routing])

    return HttpResponse('{"msg": "OK"}', content_type='application/json')


def cron_task(request):
    site = request.GET.get('site', None)
    network_id = request.GET.get('network_id', None)
    routing = '%s%s' % (site, network_id)
    return render(request, 'core/index.html', {'routing': routing, 'site': site, 'network_id': network_id})
