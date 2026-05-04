from django.contrib import admin

from .models import Camera, Recording


@admin.register(Camera)
class CameraAdmin(admin.ModelAdmin):
    list_display = ('name', 'source_type', 'mode', 'is_active', 'updated_at')
    list_filter = ('source_type', 'mode', 'is_active')
    search_fields = ('name',)


@admin.register(Recording)
class RecordingAdmin(admin.ModelAdmin):
    list_display = ('camera', 'started_at', 'ended_at', 'duration_seconds', 'is_finalized')
    list_filter = ('camera', 'is_finalized')
    date_hierarchy = 'started_at'
    readonly_fields = ('file_path', 'started_at', 'ended_at', 'duration_seconds', 'file_size_bytes')
