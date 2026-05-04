from django.db import models


class Camera(models.Model):
    SOURCE_BROWSER = 'browser'
    SOURCE_LOCAL = 'local'
    SOURCE_RTSP = 'rtsp'
    SOURCE_CHOICES = [
        (SOURCE_BROWSER, 'Browser (WebRTC / MediaRecorder dari client)'),
        (SOURCE_LOCAL, 'Local device (cv2 di mesin Django)'),
        (SOURCE_RTSP, 'RTSP / IP camera'),
    ]

    MODE_LIVE_ONLY = 'live_only'
    MODE_CCTV = 'cctv'
    MODE_CHOICES = [
        (MODE_LIVE_ONLY, 'Live only (tidak merekam)'),
        (MODE_CCTV, 'CCTV (rekam segmen 30 menit)'),
    ]

    name = models.CharField(max_length=100)
    source_type = models.CharField(max_length=16, choices=SOURCE_CHOICES, default=SOURCE_BROWSER)
    source_config = models.JSONField(default=dict, blank=True)
    mode = models.CharField(max_length=16, choices=MODE_CHOICES, default=MODE_LIVE_ONLY)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.get_source_type_display()})"


class Recording(models.Model):
    camera = models.ForeignKey(Camera, on_delete=models.CASCADE, related_name='recordings')
    file_path = models.CharField(max_length=512)
    started_at = models.DateTimeField(db_index=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(null=True, blank=True)
    file_size_bytes = models.PositiveBigIntegerField(null=True, blank=True)
    is_finalized = models.BooleanField(default=False)

    class Meta:
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['camera', '-started_at']),
        ]

    def __str__(self):
        return f"{self.camera.name} @ {self.started_at:%Y-%m-%d %H:%M}"
