from django.contrib import admin

from .models import CollectionRoute, RouteStop


class RouteStopInline(admin.TabularInline):
    model = RouteStop
    extra = 0
    readonly_fields = ('stop_order', 'latitude', 'longitude')


@admin.register(CollectionRoute)
class CollectionRouteAdmin(admin.ModelAdmin):
    list_display = ('name', 'cooperative', 'is_active', 'day_of_week', 'estimated_distance_km', 'stop_count', 'created_at')
    list_filter = ('is_active', 'day_of_week', 'cooperative')
    search_fields = ('name', 'description')
    inlines = [RouteStopInline]

    def stop_count(self, obj):
        return obj.stops.count()
    stop_count.short_description = 'Stops'


@admin.register(RouteStop)
class RouteStopAdmin(admin.ModelAdmin):
    list_display = ('route', 'stop_order', 'latitude', 'longitude', 'estimated_minutes', 'farmer_count')
    list_filter = ('route__cooperative',)
    search_fields = ('route__name',)

    def farmer_count(self, obj):
        return obj.farmers.count()
    farmer_count.short_description = 'Farmers'
