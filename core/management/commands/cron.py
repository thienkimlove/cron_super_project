import datetime
import re
import time
from urllib.parse import unquote, urlparse, parse_qs

import pytz
import requests
import json
import pycountry
from django.db.models import Q
from gevent.pool import Pool
import urllib3
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from django.core.management.base import BaseCommand, CommandError
from django import db
from pyparsing import basestring
from urllib3.exceptions import MaxRetryError

from core.models import *
from django.db import connection
from django.apps import apps

from project.settings import LOG_FILE, LOG_CRON_DIRECTORY, TEST_JSON


def debug(msg):
    with open(LOG_FILE, 'r') as original: data = original.read()
    with open(LOG_FILE, 'w') as modified: modified.write(data + str(repr(msg)) + "\n")


def country_list():
    cc = {}
    t = list(pycountry.countries)

    for country in t:
        cc[country.alpha_2] = country.name
    return cc


def get_device_from_string(value):
    new_str = '   ' + value

    new_str = new_str.replace(',', '  ')
    new_str = new_str.replace('``', '  ')
    new_str = new_str.replace('-', '  ')
    new_str = new_str.replace('_', '  ')

    temp = ' '.split(new_str)
    return ','.join(temp)


def get_country_codes_from_string(value):
    new_str = value.replace(',', '  ')
    new_str = new_str.replace('``', '  ')
    new_str = new_str.replace('-', '  ')
    new_str = new_str.replace('_', '  ')
    new_str = '   ' + new_str + '   '

    regex = r"\s*\[?([A-Z]{2})\]?\s*"

    get_list = []
    result = re.findall(regex, new_str, re.IGNORECASE)
    countries = country_list()
    if result:
        for find in result:
            if (find in countries.keys() or find == 'UK') and find not in get_list:
                get_list.append(find)
            else:
                debug(find)

    if get_list:
        return ','.join(get_list)
    else:
        debug(new_str)
        # debug(countries.keys())
    return None


def get_url(url):
    urllib3.disable_warnings()
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
    session = requests.session()
    session.max_redirects = 10
    session.verify = False
    session.timeout = (20, 20)

    url = unquote(url)
    o = urlparse(url)
    query = parse_qs(o.query, True)
    url_short = o._replace(query=None).geturl()
    query['limit'] = 10000
    if 'user' in query and 'pass' in query:
        g = session.get(url_short, params=query, auth=(query['user'][0], query['pass'][0]))
    else:
        g = session.get(url_short, params=query)

    try:
        response_json = g.content.decode('utf-8').replace('\0', '')
        return json.loads(response_json)
    except Exception as e:
        return json.loads('{"Error": %s}' % e)


def process(response, network, site, stdout):
    if 'offers' in response:
        raw_content = response.get('offers')
    elif 'response' in response:
        raw_content = response.get('response').get('data')
    elif 'data' in response and 'rowset' in response.get('data'):
        raw_content = response.get('data').get('rowset')
    else:
        raw_content = response

    write_log(site, network.id, 'Have Raw Content')

    stdout.write('Have Raw Content')
    stdout.write("<br/>")

    if raw_content:
        if isinstance(raw_content, dict):
            raw_content = raw_content.values()

        offer_pool = Pool(1000)
        db.connections.close_all()
        for content in raw_content:
            if isinstance(content, dict):
                if 'Offer' in content:
                    offer_pool.spawn(parse_offer, content.get('Offer'), network, site, stdout)
                else:
                    offer_pool.spawn(parse_offer, content, network, site, stdout)

        offer_pool.join()


def get_device(content):
    if isinstance(content, int) or isinstance(content, basestring):
        return None

    if 'devices' in content:
        return content.get('devices')

    if 'Platforms' in content:
        return content.get('Platforms')

    if 'platform' in content:
        return content.get('platform')

    if 'offer_platform' in content and 'target' in content.get('offer_platform'):
        return content.get('offer_platform').get('target')

    if 'payments' in content:
        payments = content.get('payments')
        if isinstance(payments, list):
            for payment in payments:
                if 'os' in payment and payment.get('os'):
                    return payment.get('os')

    if 'payments' in content:
        payments = content.get('payments')
        if isinstance(payments, list):
            for payment in payments:
                if 'devices' in payment and payment.get('devices'):
                    return payment.get('devices')


def get_payout(content):
    if isinstance(content, int) or isinstance(content, basestring):
        return None

    if 'payout' in content:
        return content.get('payout')

    if 'offer' in content and 'payout' in content.get('offer'):
        return content.get('offer').get('payout')

    if 'default_payout' in content:
        return content.get('default_payout')

    if 'rate' in content:
        return content.get('rate')

    if 'payments' in content:
        payments = content.get('payments')
        if isinstance(payments, list):
            for payment in payments:
                if 'revenue' in payment:
                    return payment.get('revenue')
        if isinstance(payments, dict):
            if 'revenue' in payments:
                return payments.get('revenue')

    if 'Payout' in content:
        return content.get('Payout')
    return None


def get_redirect_link(content):
    if isinstance(content, int) or isinstance(content, basestring):
        return None

    if 'tracking_link' in content:
        return content.get('tracking_link')

    if 'offer' in content and 'tracking_link' in content.get('offer'):
        return content.get('offer').get('tracking_link')

    if 'tracking_url' in content:
        return content.get('tracking_url')

    if 'Tracking_url' in content:
        return content.get('Tracking_url')

    if 'offer_url' in content:
        return content.get('offer_url')

    if 'link' in content:
        return content.get('link')


def get_geo_locations(content):
    if isinstance(content, int) or isinstance(content, basestring):
        return None

    if 'countries' in content:
        geo_string = []
        for country in content.get('countries'):
            if 'code' in country:
                geo_string.append(country.get('code'))
            else:
                geo_string.append(country)
        return ', '.join(geo_string)

    if 'offer_geo' in content and 'target' in content.get('offer_geo'):
        geo_string = []
        for country in content.get('offer_geo').get('target'):
            if 'country_code' in country:
                geo_string.append(country.get('country_code'))
        return ', '.join(geo_string)

    if 'geos' in content:
        return ', '.join(content.get('geos'))
    if 'Countries' in content:
        return content.get('Countries')

    if 'geo' in content:
        return content.get('geo')

    if 'payments' in content:
        payments = content.get('payments')
        if isinstance(payments, list):
            for payment in payments:
                if 'countries' in payment:
                    countries = payment.get('countries')
                    if not countries:
                        return ', '.join(['US', 'GB'])
                    return ', '.join(countries)


def get_net_offer_id(content):
    if isinstance(content, int) or isinstance(content, basestring):
        return None

    if 'offer_id' in content:
        return content.get('offer_id')

    if 'offer' in content and 'id' in content.get('offer'):
        return content.get('offer').get('id')

    if 'offerid' in content:
        return content.get('offerid')

    if 'ID' in content:
        return content.get('ID')

    if 'id' in content:
        return content.get('id')

    return None


def get_offer_name(content):
    if isinstance(content, int) or isinstance(content, basestring):
        return None

    if 'name' in content:
        return content.get('name')

    if 'Name' in content:
        return content.get('Name')

    if 'offer_name' in content:
        return content.get('offer_name')

    if 'app_name' in content:
        return content.get('app_name')

    if 'title' in content:
        return content.get('title')

    if 'offer' in content and 'name' in content.get('offer'):
        return content.get('offer').get('name')

    return None


def parse_offer(content, network, site, stdout):
    offer_name = get_offer_name(content)
    if offer_name:
        offer_name = str(offer_name)[:191]
    else:
        stdout.write('Can not get offer_name for offer with content=%s' % repr(content))
        stdout.write("<br/>")

    payout = get_payout(content)

    if payout:
        payout = str(payout).replace('$', '')
        if network.rate_offer > 0:
            payout = round(float(payout) / int(network.rate_offer), 2)
        else:
            payout = round(float(payout), 2)

    else:
        stdout.write('Can not get payout for offer with content=%s' % repr(content))
        stdout.write("<br/>")

    net_offer_id = get_net_offer_id(content)

    if net_offer_id:
        net_offer_id = int(net_offer_id)
    else:
        stdout.write('Can not get net_offer_id for offer with content=%s' % repr(content))
        stdout.write("<br/>")

    geo_locations = get_geo_locations(content)

    if not geo_locations and offer_name:
        geo_locations = get_country_codes_from_string(offer_name)

    if geo_locations:
        geo_locations = geo_locations.replace('|', ',')
    else:
        stdout.write('Can not get geo_locations for offer with content=%s' % repr(content))
        stdout.write("<br/>")

    devices = get_device(content)

    is_iphone = False
    is_ipad = False
    android = False
    ios = False
    real_device = 1

    if not devices and offer_name:
        devices = get_device_from_string(offer_name)

    if devices:
        if isinstance(devices, basestring):
            if ',' in devices:
                devices = devices.split(',')

        if isinstance(devices, dict):
            devices = devices.values()

        for device in devices:
            if isinstance(device, dict) and 'device_type' in device:
                temp_device = str(device.get('device_type')).lower()
            else:
                temp_device = str(device).lower()

            if 'ios' in temp_device:
                ios = True

            if 'droid' in temp_device:
                android = True

            if 'ipad' in temp_device:
                is_ipad = True

            if 'iphone' in temp_device:
                is_iphone = True

        if ios and android:
            real_device = 2
        elif android:
            real_device = 4
        elif ios:
            real_device = 5
        elif is_ipad:
            real_device = 6
        elif is_iphone:
            real_device = 7

    else:
        stdout.write('Can not get devices for offer with content=%s' % repr(content))
        stdout.write("<br/>")

    redirect_link = get_redirect_link(content)

    if not redirect_link:
        if net_offer_id and 'adwool' in network.cron:
            get_link_through_api = 'https://adwool.api.hasoffers.com/Apiv3/json?api_key=af74bc02809fe0089e860b387d2f8a20735529b744cbcabc750b7564c804bb1a&Target=Affiliate_Offer&Method=generateTrackingLink&offer_id=' + str(
                net_offer_id)
            stdout.write('Start get link through API!')
            stdout.write("<br/>")
            link_response = None
            try:
                link_response = get_url(get_link_through_api)
            except Exception as e:
                stdout.write(repr(e))
                stdout.write("<br/>")
            if link_response is not None:
                if 'response' in link_response and 'data' in link_response.get(
                        'response') and 'click_url' in link_response.get('response').get('data'):
                    redirect_link = link_response.get('response').get('data').get('click_url')

    if redirect_link:
        redirect_link += '&aff_sub=#subId'

    if redirect_link and net_offer_id and geo_locations and payout and offer_name:

        datetime_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        Offer.objects.using(site).update_or_create(
            net_offer_id=net_offer_id, network=network,
            defaults={
                'name': offer_name,
                'click_rate': payout,
                'redirect_link': redirect_link,
                'geo_locations': geo_locations,
                'allow_devices': real_device,
                'number_when_click': network.virtual_click,
                'number_when_lead': network.virtual_lead,
                'status': True,
                'auto': True,
                'updated_at': datetime_str,
                'created_at': datetime_str,
            },
        )

        stdout.write('OK with net_offer_id=%s' % net_offer_id)
        stdout.write("<br/>")
    return None


def write_log(site, network_id, message):
    pass
    # filename = LOG_CRON_DIRECTORY + '/' + site + '_' + str(network_id)
    # with open(filename, 'r') as original: data = original.read()
    # with open(filename, 'w') as modified: modified.write(data + message+"\n")


def logistic(url, network, site, stdout):
    response_data = get_url(url)
    process(response_data, network, site, stdout)


def cron_one(site, network, stdout):
    stdout.write('Start with network_id=%s for site=%s' % (network.id, site))
    stdout.write("<br/>")
    Offer.objects.using(site).filter(network=network).filter(net_offer_id__isnull=True).delete()
    response = None
    try:
        if network.id == 222:
            with open(TEST_JSON, 'r') as original:
                response = original.read()
            response = json.loads(response)
        else:
            response = get_url(network.cron)
        write_log(site, network.id, 'Have response')
        stdout.write('Have response')
        stdout.write("<br/>")
    except Exception as e:
        stdout.write('Exception %s' % repr(e))
        stdout.write("<br/>")

    list_extra_url = []
    if response is not None:
        total_page = None
        total_limit = None

        if 'response' in response:
            response = response.get('response')

        if 'data' in response and 'data' in response.get('data'):
            response = response.get('data').get('data')

        if 'data' in response and 'totalPages' in response.get('data'):
            total_page = response.get('data').get('totalPages')
            total_limit = response.get('data').get('limit')

        if total_page is not None and total_limit is not None:
            for item in list(range(total_page)):
                url_extra = network.cron + '&limit=' + str(total_limit) + '&offset=' + str(item * total_limit)
                list_extra_url.append(url_extra)

        if list_extra_url:
            stdout.write('Start process with list of urls')
            stdout.write("<br/>")
            process_pool = Pool()
            for url in list_extra_url:
                process_pool.spawn(logistic, url, network, site, stdout)
            process_pool.join()
        else:
            stdout.write('Start process with response')
            stdout.write("<br/>")
            process(response, network, site, stdout)

    CronLog.objects.filter(site=site).filter(network_id=network.id).delete()
    CronLog.objects.create(site=site, network_name=network.name, network_id=network.id, log='Not write')
    stdout.write('End with network_id=%s for site=%s' % (network.id, site))
    stdout.write("<br/>")


def cron_for_network(site, stdout):
    networks = Network.objects.using(site).exclude(cron='').all()
    pool = Pool()
    for network in networks:
        if network.cron:
            pool.spawn(cron_one, site, network, stdout)
    pool.join()


class Command(BaseCommand):
    help = 'Run cron network every days'

    def add_arguments(self, parser):
        parser.add_argument('network', nargs='+', type=str)

    def handle(self, *args, **options):
        start_time = time.time()

        for site in options['network']:
            cron_for_network(site, self.stdout)

        # test = get_country_codes_from_string('BetVictor Casino Slots &amp;amp; Games #3 - iPhone,iPad - UK (S)')
        # stdout.write(test)
        end_time = time.time()

        self.stdout.write(self.style.SUCCESS('Successfully end clicks in "%s"' % (end_time - start_time)))
