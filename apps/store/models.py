from django.db import models

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
COUNTRY_COORDINATES = {
    'mx': (23.6345, -102.5528),
    'es': (40.4168, -3.7038),
    'ar': (-34.6037, -58.3816),
    'co': (4.7110, -74.0721),
    'cl': (-33.4489, -70.6693),
    'us': (37.0902, -95.7129),
    'pe': (-9.1900, -75.0152),
    'uy': (-34.9011, -56.1645),
}


class Vendor(models.Model):
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255, blank=True, null=True)
    contact_email = models.EmailField(blank=True, null=True)
    contact_phone = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return self.name


class Location(models.Model):
    COUNTRY_CHOICES = COUNTRY_CHOICES

    city = models.CharField(max_length=255, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    latitude = models.FloatField()
    longitude = models.FloatField()
    country = models.CharField(max_length=4, choices=COUNTRY_CHOICES, default='es')

    class Meta:
        verbose_name_plural = 'Locations'
        unique_together = ('latitude', 'longitude')

    def __str__(self):
        return (
            f"{self.city}, {self.address}"
            if self.address
            else f'{self.city} ({self.latitude}, {self.longitude})'
        )


class Store(models.Model):
    STORE_TYPE_CHOICES = [
        ('store', 'Store'),
        ('dispensary', 'Dispensary'),
    ]
    name = models.CharField(max_length=255)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='stores')
    location = models.OneToOneField(Location, on_delete=models.CASCADE)
    store_type = models.CharField(
        max_length=20, choices=STORE_TYPE_CHOICES, default='store'
    )
    logo = models.ImageField(upload_to='store_logos/', blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    opening_hours = models.JSONField(blank=True, null=True)

    def __str__(self):
        return self.name
