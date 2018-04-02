import re
import time
from urllib.parse import unquote, urlparse, parse_qs

import MySQLdb
import requests
import json
import pycountry
from gevent.pool import Pool
import urllib3
from django.core.management.base import BaseCommand, CommandError
from pyparsing import basestring
from urllib3.exceptions import MaxRetryError

from core.management.commands.cron import cron_one, rabit_send
from core.models import *
from django.db import connection
from django.apps import apps

from project.settings import LOG_FILE, LOG_CRON_DIRECTORY


class Command(BaseCommand):

    help = 'Run cron network every days'

    def add_arguments(self, parser):
        parser.add_argument(
            '--site', dest='site', required=True,
            help='the site identify',
        )

        parser.add_argument(
            '--network_id', dest='network_id', required=True,
            help='the network id inside site',
        )

        parser.add_argument(
            '--routing', dest='routing', required=True,
            help='dynamic routing for each call',
        )

    def handle(self, *args, **options):
        site = options['site']
        routing = options['routing']
        network = Network.objects.using(site).get(pk=options['network_id'])
        rabit_send('Start getting data from URL. Please wait...', routing)
        cron_one(site, network, routing)

        self.stdout.write('Done')

