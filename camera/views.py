from django.http import StreamingHttpResponse, HttpResponse
from django.shortcuts import render
import cv2
import os
import time
from django.conf import settings

# Variabel global untuk kamera
camera = None

def index(request):
    return render(request, 'camera/index.html')

camera = cv2.VideoCapture(0)


def start_camera(request):
    global camera
    if camera is None:
        camera = cv2.VideoCapture(0)  # Menggunakan kamera default
        if not camera.isOpened():
            return HttpResponse("Failed to open camera")
    return HttpResponse("Camera started")


def stop_camera(request):
    global camera
    if camera is not None:
        camera.release()  # Hentikan dan lepas kamera
        camera = None
    return HttpResponse("Camera stopped")


def video_stream():
    global camera
    if camera is not None and camera.isOpened():
        # Setup untuk menyimpan video
        frame_width = int(camera.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
        frame_rate = int(camera.get(cv2.CAP_PROP_FPS)) or 20  # Jika tidak ada FPS, gunakan 20
        start_time = time.time()

        # Membuat VideoWriter untuk menyimpan video
        video_writer = None
        video_count = 1

        while True:
            ret, frame = camera.read()  # Membaca frame dari kamera
            if not ret:
                print("Failed to grab frame")  # Debug: Menambahkan pesan jika frame gagal
                break

            print("Frame captured")  # Debug: Menambahkan pesan jika frame berhasil
            
            # Simpan frame ke video setiap 30 detik
            current_time = time.time()
            if (current_time - start_time) >= 30:  # Setiap 30 detik
                if video_writer:
                    video_writer.release()  # Selesai dengan video lama
                # Buat video baru
                video_filename = os.path.join(settings.VIDEOS_DIR, f'video_{video_count}.mp4')
                video_writer = cv2.VideoWriter(video_filename, cv2.VideoWriter_fourcc(*'mp4v'), 
                                               frame_rate, (frame_width, frame_height))
                video_count += 1
                start_time = current_time  # Reset timer

            # Tulis frame ke video
            if video_writer:
                video_writer.write(frame)

            # Lanjutkan dengan streaming video ke client
            _, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

        if video_writer:
            video_writer.release() 

    else:
        yield (b'--frame\r\n'
               b'Content-Type: text/plain\r\n\r\nCamera is not available\r\n')
def video_stream_view(request):
    return StreamingHttpResponse(video_stream(), content_type='multipart/x-mixed-replace; boundary=frame')


def livestream(request):
    return render(request, 'livestream.html')  # Halaman live stream video


def video_history(request):
    video_files = os.listdir(settings.VIDEOS_DIR)  # Ambil daftar file video di folder videos
    video_files = [os.path.join('videos', video) for video in video_files]  # Buat jalur yang benar untuk video
    context = {'video_files': video_files}
    return render(request, 'camera/history.html', context)
