from django.db import models

from apps.base.models import CooperativeScopedModel


class DayOfWeek(models.IntegerChoices):
    MONDAY = 0, 'Monday'
    TUESDAY = 1, 'Tuesday'
    WEDNESDAY = 2, 'Wednesday'
    THURSDAY = 3, 'Thursday'
    FRIDAY = 4, 'Friday'
    SATURDAY = 5, 'Saturday'
    SUNDAY = 6, 'Sunday'


class CollectionRoute(CooperativeScopedModel):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    path = models.JSONField(default=dict)
    is_active = models.BooleanField(default=True)
    estimated_distance_km = models.DecimalField(
        max_digits=7, decimal_places=2, null=True, blank=True,
    )
    day_of_week = models.IntegerField(null=True, blank=True, choices=DayOfWeek.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Collection Route'
        verbose_name_plural = 'Collection Routes'
        ordering = ['name']

    def __str__(self):
        return self.name


class RouteStop(models.Model):
    route = models.ForeignKey(
        CollectionRoute, on_delete=models.CASCADE,
        related_name='stops',
    )
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    stop_order = models.PositiveSmallIntegerField()
    estimated_minutes = models.PositiveSmallIntegerField(null=True, blank=True)
    farmers = models.ManyToManyField(
        'farmers.Farmer', blank=True,
        related_name='route_stops',
    )

    class Meta:
        ordering = ['stop_order']
        unique_together = [('route', 'stop_order')]

    def __str__(self):
        return f'{self.route.name} — Stop {self.stop_order}'
