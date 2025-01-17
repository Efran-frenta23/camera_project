from django.shortcuts import render
from django.http import JsonResponse
import cv2
import threading
import time

# Variabel global untuk mengontrol thread kamera
camera_thread = None
is_running = False

# Fungsi untuk membuka kamera dan menyimpan video setiap 30 detik
def open_camera():
    global is_running
    cap = cv2.VideoCapture(0)  # Buka webcam
    
    if not cap.isOpened():
        return  # Jika kamera gagal dibuka, keluar dari fungsi
    
    # Mengatur resolusi video yang akan disimpan (misal 640x480)
    frame_width = int(cap.get(3))
    frame_height = int(cap.get(4))
    
    # Menghitung durasi 30 detik
    interval_duration = 30  # detik
    start_time = time.time()
    video_index = 0
    
    # Membuat writer untuk menyimpan video
    fourcc = cv2.VideoWriter_fourcc(*'XVID')

    while is_running:
        # Membuat nama file baru setiap 30 detik
        if time.time() - start_time >= interval_duration:
            video_index += 1
            start_time = time.time()

        # Nama file video
        video_filename = f'output_{video_index}.avi'
        
        # Membuat VideoWriter untuk menyimpan file
        out = cv2.VideoWriter(video_filename, fourcc, 20.0, (frame_width, frame_height))
        
        # Capture video
        while time.time() - start_time < interval_duration and is_running:
            ret, frame = cap.read()
            if ret:
                # Tampilkan video
                cv2.imshow('Camera', frame)

                # Tulis frame ke file video
                out.write(frame)

                # Keluar jika tombol 'q' ditekan
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    is_running = False
                    break
        
        # Tutup VideoWriter ketika sudah mencapai 30 detik atau jika kamera dimatikan
        out.release()

    cap.release()
    cv2.destroyAllWindows()

# Fungsi untuk memulai kamera
def start_camera(request):
    global camera_thread, is_running
    
    if not is_running:
        is_running = True
        camera_thread = threading.Thread(target=open_camera)
        camera_thread.start()
        return JsonResponse({'message': 'Camera started'})
    else:
        return JsonResponse({'message': 'Camera is already running'})

# Fungsi untuk menghentikan kamera
def stop_camera(request):
    global is_running
    
    if is_running:
        is_running = False
        return JsonResponse({'message': 'Camera stopped'})
    else:
        return JsonResponse({'message': 'Camera is not running'})

# Fungsi untuk merender halaman index
def index(request):
    return render(request, 'camera/index.html') 
