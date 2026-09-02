from django.contrib import admin

from .models import Assignment, Holiday, Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'color', 'assignment_count', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at']

    def assignment_count(self, obj):
        return obj.assignments.count()
    assignment_count.short_description = 'Assignments'


@admin.register(Holiday)
class HolidayAdmin(admin.ModelAdmin):
    list_display = ['date', 'name', 'is_off_day']
    list_filter = ['is_off_day']
    search_fields = ['name']
    date_hierarchy = 'date'


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ['title', 'project', 'role', 'assignee', 'start_date', 'end_date']
    list_filter = ['project', 'role', 'start_date']
    search_fields = ['title', 'assignee']
    date_hierarchy = 'start_date'
    autocomplete_fields = ['project']
