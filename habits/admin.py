from django.contrib import admin

from .models import Habit


@admin.register(Habit)
class HabitAdmin(admin.ModelAdmin):
    list_display = ('id', 'action', 'time', 'place', 'user', 'is_pleasant', 'is_public', 'periodicity')
    list_filter = ('is_pleasant', 'is_public', 'periodicity')
    search_fields = ('action', 'place', 'reward', 'user__email')
    readonly_fields = ('last_reminded_at', 'created_at')
