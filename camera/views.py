from django.http import StreamingHttpResponse, HttpResponse
from django.shortcuts import render
import cv2
import os
import time
from django.conf import settings
import subprocess

# Variabel global untuk kamera
camera = None

def index(request):
    return render(request, 'camera/index.html')

# Menggunakan kamera default (bisa diubah ke USB kamera nanti)
def start_camera(request):
    global camera
    camera_type = request.GET.get('camera_type', 'default')  # Dapatkan tipe kamera dari request
    if camera is not None:
        camera.release()  # Lepas kamera yang mungkin sudah aktif sebelumnya

    if camera_type == 'usb':
        camera = cv2.VideoCapture(1)  # Menggunakan kamera USB (ganti index jika diperlukan)
    else:
        camera = cv2.VideoCapture(0)  # Kamera default

    if not camera.isOpened():
        return HttpResponse("Failed to open camera")

    return HttpResponse(f"Camera {camera_type} started")

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
        frame_rate = int(camera.get(cv2.CAP_PROP_FPS)) or 20  # Gunakan 20 FPS jika tidak terdeteksi

        # Membuat VideoWriter untuk menyimpan video
        video_writer = None
        video_count = 1
        start_time = time.time()

        while True:
            ret, frame = camera.read()  # Membaca frame dari kamera
            if not ret:
                print("Failed to grab frame")  # Debug: Tambahkan pesan jika gagal mendapatkan frame
                break

            # Simpan frame ke video setiap 30 detik
            current_time = time.time()
            if (current_time - start_time) >= 30:  # Setiap 30 detik
                if video_writer:
                    video_writer.release()  # Selesai dengan video lama

                    # Konversi video ke H.264 menggunakan FFmpeg
                    input_filename = video_filename
                    output_filename = os.path.join(settings.VIDEOS_DIR, f'video_{video_count}_h264.mp4')

                    ffmpeg_command = [
                        'ffmpeg', '-i', input_filename,  # Input file
                        '-c:v', 'libx264',  # Codec video H.264
                        '-preset', 'slow',  # Pilih preset kompresi
                        '-crf', '22',  # Pilih kualitas
                        '-c:a', 'aac',  # Codec audio
                        '-b:a', '128k',  # Bitrate audio
                        output_filename  # Output file
                    ]

                    subprocess.run(ffmpeg_command)  # Eksekusi konversi

                    # Hapus file video sementara
                    if os.path.exists(input_filename):
                        os.remove(input_filename)

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
    return render(request, 'camera/livestream.html')  # Halaman live stream video


def video_history(request):
    video_files = os.listdir(settings.VIDEOS_DIR)  # Ambil daftar file video di folder videos
    video_files = [str(os.path.join('videos', video)).replace("videos", "/media") for video in video_files]  # Buat jalur yang benar untuk video
    context = {'video_files': video_files}
    print(context)
    return render(request, 'camera/history.html', context)
