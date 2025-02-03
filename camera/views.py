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
camera = cv2.VideoCapture()  # Inisialisasi kamera default atau eksternal

def find_external_camera():
    """
    Mencoba mendeteksi kamera eksternal dengan mengiterasi indeks kamera (1 s/d 10).
    Mengembalikan objek cv2.VideoCapture jika ditemukan, jika tidak, None.
    """
    for idx in range(1, 11):  # Ubah rentang sesuai kebutuhan
        cap = cv2.VideoCapture(idx)
        if cap.isOpened():
            # Opsional: bisa menambahkan pengecekan properti khusus jika diperlukan
            return cap
        else:
            cap.release()
    return None

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
    if camera and camera.isOpened():
        camera.release()

    # Logika untuk memilih kamera
    if camera_type == 'internal':
        internal_camera = cv2.VideoCapture(0)  # Kamera internal biasanya di index 0
        if not internal_camera.isOpened():
            return HttpResponse("Failed to open internal camera")

    elif camera_type == 'usb':
        # Cari kamera eksternal secara otomatis (tanpa harus menentukan indeks secara manual)
        external_camera = find_external_camera()
        if not external_camera or not external_camera.isOpened():
            return HttpResponse("Failed to open external (USB) camera")

    elif camera_type == 'default':
        camera.open(0)
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

    # Pastikan direktori untuk video ada
    os.makedirs(settings.VIDEOS_DIR, exist_ok=True)

    video_writer = None
    video_count = 1
    start_time = time.time()
    video_filename = None

    while True:
        frame = None
        # Prioritaskan pembacaan frame dari kamera yang aktif
        for cam in [internal_camera, external_camera, camera]:
            if cam and cam.isOpened():
                ret, temp_frame = cam.read()
                if ret:
                    frame = temp_frame
                    break

        if frame is not None:
            # Inisialisasi properti video (hanya sekali)
            if frame_width is None or frame_height is None:
                
                frame_height, frame_width = frame.shape[:2]
                frame_rate = int(cam.get(cv2.CAP_PROP_FPS)) or 30

            current_time = time.time()
            # Setiap 15 detik, simpan video yang sedang berjalan dan mulai yang baru
            if (current_time - start_time) >= 15:
                if video_writer:
                    video_writer.release()

                    # Pastikan file input ada sebelum menjalankan FFmpeg
                    if video_filename and os.path.exists(video_filename):
                        output_filename = os.path.join(settings.VIDEOS_DIR, f'video_{video_count}_h264.mp4')
                        ffmpeg_command = [
                            'ffmpeg', '-y', '-i', video_filename,
                            '-c:v', 'libx264', '-preset', 'slow',
                            '-crf', '22', '-c:a', 'aac', '-b:a', '128k',
                            output_filename
                        ]
                        try:
                            subprocess.run(ffmpeg_command, check=True)
                        except subprocess.CalledProcessError as e:
                            print(f"Error during FFmpeg conversion: {e}")
                        # Hapus file input setelah konversi berhasil
                        if os.path.exists(video_filename):
                            os.remove(video_filename)
                    else:
                        print(f"File {video_filename} tidak ditemukan, tidak dapat dikonversi.")

                # Buat file video baru
                video_filename = os.path.join(settings.VIDEOS_DIR, f'video_{video_count}.mp4')
                video_writer = cv2.VideoWriter(
                    video_filename,
                    cv2.VideoWriter_fourcc(*'mp4v'),
                    frame_rate,
                    (frame_width, frame_height)
                )
                video_count += 1
                start_time = current_time

            # Tulis frame ke video jika video_writer aktif
            if video_writer:
                video_writer.write(frame)

            # Streaming frame sebagai JPEG
            ret_enc, buffer = cv2.imencode('.jpg', frame)
            if ret_enc:
                frame_bytes = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            else:
                yield (b'--frame\r\n'
                       b'Content-Type: text/plain\r\n\r\nFailed to encode frame\r\n')
        else:
            # Jika tidak ada frame, kirimkan pesan error melalui stream
            yield (b'--frame\r\n'
                   b'Content-Type: text/plain\r\n\r\nNo frames available\r\n')

    # Pastikan video_writer dilepas saat keluar dari loop
    if video_writer:
        video_writer.release()

def video_stream_view(request):
    return StreamingHttpResponse(video_stream(),
                                 content_type='multipart/x-mixed-replace; boundary=frame')

def livestream(request):
    return render(request, 'camera/livestream.html')

def video_history(request):
    video_files = os.listdir(settings.VIDEOS_DIR)
    # Ubah path file video untuk diakses via URL (misal: /media/)
    video_files = [os.path.join(settings.MEDIA_URL, 'videos', video) for video in video_files]
    context = {'video_files': video_files}
    print(context)
    return render(request, 'camera/history.html', context)
