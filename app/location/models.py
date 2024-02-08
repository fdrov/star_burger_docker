from django.db import models


class Location(models.Model):
    address = models.CharField(
        'Адрес',
        max_length=500,
        unique=True,
    )
    latitude = models.DecimalField(
        'Широта',
        max_digits=9,
        decimal_places=6
    )
    longitude = models.DecimalField(
        'Долгота',
        max_digits=9,
        decimal_places=6
    )
    generated_at = models.DateTimeField(
        'Когда были получены координаты',
        auto_now=True,
    )

    class Meta:
        verbose_name = 'Локация'
        verbose_name_plural = 'Локации'

    def __str__(self):
        return f'{self.address} → ({self.latitude}, {self.longitude})'
