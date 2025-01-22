from django.http import StreamingHttpResponse, HttpResponse
from django.shortcuts import render
import cv2
import os
import time
from django.conf import settings
import subprocess

# Variabel global untuk kamera
internal_camera = None
external_camera = None
camera = cv2.VideoCapture()  # Kamera default atau eksternal

def index(request):
    return render(request, 'camera/index.html')

def start_camera(request):
    global internal_camera, external_camera, camera
    camera_type = request.GET.get('camera_type', 'default')  # Dapatkan tipe kamera dari request

    # Lepaskan kamera sebelumnya jika ada
    if internal_camera and internal_camera.isOpened():
        internal_camera.release()
    if external_camera and external_camera.isOpened():
        external_camera.release()

    # Logika untuk memilih kamera
    if camera_type == 'internal':
        internal_camera = cv2.VideoCapture(0)  # Kamera internal biasanya di index 0
        if not internal_camera.isOpened():
            return HttpResponse("Failed to open internal camera")

    elif camera_type == 'usb':
        external_camera = cv2.VideoCapture(2)  # Kamera USB biasanya di index 2
        if not external_camera.isOpened():
            return HttpResponse("Failed to open USB camera")

    elif camera_type == 'both':
        internal_camera = cv2.VideoCapture(0)  # Kamera internal
        external_camera = cv2.VideoCapture(2)  # Kamera USB
        if not internal_camera.isOpened() or not external_camera.isOpened():
            return HttpResponse("Failed to open both cameras")

    elif camera_type == 'default':
        if not camera.isOpened():
            return HttpResponse("Failed to open default camera")

    return HttpResponse(f"Camera {camera_type} started")

def stop_camera(request):
    global internal_camera, external_camera, camera
    if internal_camera and internal_camera.isOpened():
        internal_camera.release()
        internal_camera = None
    if external_camera and external_camera.isOpened():
        external_camera.release()
        external_camera = None
    if camera and camera.isOpened():
        camera.release()
        camera = None
    return HttpResponse("Camera stopped")

def video_stream():
    global internal_camera, external_camera, camera
    frame_width, frame_height, frame_rate = None, None, 20  # Default frame rate jika tidak terdeteksi

    # Setup VideoWriter untuk menyimpan video
    video_writer = None
    video_count = 1
    start_time = time.time()

    while True:
        frame = None
        if internal_camera and internal_camera.isOpened():
            ret, frame_internal = internal_camera.read()  # Baca frame dari kamera internal
            if ret:
                frame = frame_internal  # Gunakan frame dari internal

        if external_camera and external_camera.isOpened():
            ret, frame_external = external_camera.read()  # Baca frame dari kamera eksternal
            if ret:
                frame = frame_external  # Gunakan frame dari eksternal

        if camera and camera.isOpened():
            ret, frame_default = camera.read()  # Baca frame dari kamera default
            if ret:
                frame = frame_default  # Gunakan frame dari default

        if frame is not None:
            if not frame_width or not frame_height:
                frame_width = int(camera.get(cv2.CAP_PROP_FRAME_WIDTH))
                frame_height = int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
                frame_rate = int(camera.get(cv2.CAP_PROP_FPS)) or 20

            # Simpan frame ke video setiap 30 detik
            current_time = time.time()
            if (current_time - start_time) >= 30:
                if video_writer:
                    video_writer.release()

                    # Konversi video ke H.264 menggunakan FFmpeg
                    input_filename = video_filename
                    output_filename = os.path.join(settings.VIDEOS_DIR, f'video_{video_count}_h264.mp4')

                    ffmpeg_command = [
                        'ffmpeg', '-i', input_filename,
                        '-c:v', 'libx264', '-preset', 'slow',
                        '-crf', '22', '-c:a', 'aac', '-b:a', '128k',
                        output_filename
                    ]

                    subprocess.run(ffmpeg_command)

                    if os.path.exists(input_filename):
                        os.remove(input_filename)

                video_filename = os.path.join(settings.VIDEOS_DIR, f'video_{video_count}.mp4')
                video_writer = cv2.VideoWriter(video_filename, cv2.VideoWriter_fourcc(*'mp4v'), frame_rate, (frame_width, frame_height))
                video_count += 1
                start_time = current_time

            if video_writer:
                video_writer.write(frame)

            _, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        else:
            yield (b'--frame\r\n'
                   b'Content-Type: text/plain\r\n\r\nNo frames available\r\n')

        if video_writer:
            video_writer.release()

def video_stream_view(request):
    return StreamingHttpResponse(video_stream(), content_type='multipart/x-mixed-replace; boundary=frame')

def livestream(request):
    return render(request, 'camera/livestream.html')

def video_history(request):
    video_files = os.listdir(settings.VIDEOS_DIR)
    video_files = [str(os.path.join('videos', video)).replace("videos", "/media") for video in video_files]
    context = {'video_files': video_files}
    print(context)
    return render(request, 'camera/history.html', context)
