from django.contrib import admin
from django.urls import path
from camera import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),  # Rute untuk akses admin Django
    path('', views.index, name='index'),  # Halaman utama
    path('start_camera/', views.start_camera, name='start_camera'),  # Mulai kamera
    path('stop_camera/', views.stop_camera, name='stop_camera'),  # Hentikan kamera
    path('video_stream/', views.video_stream_view, name='video_stream'),  # Aliran video langsung
    path('livestream/', views.livestream, name='livestream'),  # Halaman live stream
    path('history/', views.video_history, name='video_history'),  # Halaman riwayat rekaman
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)