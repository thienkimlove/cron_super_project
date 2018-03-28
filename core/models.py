from django.db import models

# Create your models here.
from django.utils.text import slugify


class GeneralCharField(models.CharField):
    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 191
        super().__init__(*args, **kwargs)


class TimeStampedModel(models.Model):
    """
    An abstract base class model that provides self-updating
    ``created`` and ``modified`` fields.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        abstract = True
        ordering = ["-created_at"]

    def class_name(self):
        return self.__class__.__name__


    def __str__(self):
        if hasattr(self, 'name'):
            return "{0}".format(self.name)

class Network(TimeStampedModel):
    name= GeneralCharField()
    cron= GeneralCharField(blank=True)
    rate_offer=models.PositiveSmallIntegerField(default=0)
    virtual_click=models.PositiveSmallIntegerField(default=0)
    virtual_lead=models.PositiveSmallIntegerField(default=0)
    class Meta:
        db_table = 'networks'
        managed=False

class Offer(models.Model):
    name=GeneralCharField()
    redirect_link=GeneralCharField(blank=True, null=True)
    click_rate=models.FloatField(null=True)
    geo_locations=GeneralCharField(blank=True, null=True)
    allow_devices=models.PositiveSmallIntegerField(default=0)
    network=models.ForeignKey(Network, on_delete=models.CASCADE)
    net_offer_id=models.PositiveIntegerField(null=True)
    #image=GeneralCharField(blank=True, null=True)
    status=models.BooleanField(default=True)
    auto=models.BooleanField(default=False)
    allow_multi_lead=models.BooleanField(default=False)
    check_click_in_network=models.BooleanField(default=False)
    number_when_click=models.PositiveSmallIntegerField(default=0)
    number_when_lead=models.PositiveSmallIntegerField(default=0)
    test_link=GeneralCharField(blank=True, null=True)
    reject=models.BooleanField(default=False)
    created_at=GeneralCharField()
    updated_at=GeneralCharField()
    class Meta:
        db_table = 'offers'
        managed=False

class CronLog(TimeStampedModel):
    site=GeneralCharField()
    network_name=GeneralCharField()
    network_id=models.PositiveIntegerField()
    log=models.TextField()