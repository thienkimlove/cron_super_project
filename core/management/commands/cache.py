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

from core.management.commands.cron import cron_one
from core.models import *
from django.db import connection
from django.apps import apps

from project.settings import LOG_FILE, LOG_CRON_DIRECTORY
from django.core.cache import cache

def log_to_cache(stdout):
    stdout.write('Tao viet gi day')



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

    def handle(self, *args, **options):

        site = options['site']
        network = Network.objects.using(site).get(pk=options['network_id'])
        #cron_one(site, network, self.stdout)
        pool_list = Pool(100)

        for i in range(1, 100):
            pool_list.spawn(log_to_cache, self.stdout)
        pool_list.join()

        self.stdout.write('Done')

