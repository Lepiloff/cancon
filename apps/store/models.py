from django.db import models


class Vendor(models.Model):
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255, blank=True, null=True)
    contact_email = models.EmailField(blank=True, null=True)
    contact_phone = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return self.name


class Location(models.Model):
    COUNTRY_CHOICES = [
        ('mx', 'Mexico'),
        ('es', 'Spain'),
        ('ar', 'Argentina'),
        ('co', 'Colombia'),
        ('cl', 'Chile'),
        ('us', 'United States'),
        ('pe', 'Peru'),
        ('uy', 'Uruguay'),
    ]
    address = models.CharField(max_length=255, blank=True, null=True)
    latitude = models.FloatField()
    longitude = models.FloatField()
    country = models.CharField(max_length=4, choices=COUNTRY_CHOICES, default='es')

    class Meta:
        verbose_name_plural = 'Locations'
        unique_together = ('latitude', 'longitude')

    def __str__(self):
        return self.address or f'{self.latitude}, {self.longitude}'


class Store(models.Model):
    name = models.CharField(max_length=255)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='stores')
    location = models.OneToOneField(Location, on_delete=models.CASCADE)
    opening_hours = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.name
