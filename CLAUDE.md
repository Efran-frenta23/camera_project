# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Single-app Django project (`camera_project` / `camera`) that captures from a local camera with OpenCV, streams it as MJPEG to the browser, and writes 15-second video segments to disk that are re-encoded to H.264 with `ffmpeg` via `subprocess`. There are no models, no auth, and no tests — all behavior lives in `camera/views.py`. Comments and UI copy are in Indonesian.

## Commands

Dependencies are managed with `uv` (`uv.lock`, `.python-version` pinning Python 3.12+). Django 5.1+ and `opencv-python` are the only declared deps; `ffmpeg` must be on `PATH` for segment re-encoding to work.

```bash
uv sync                                  # install deps into .venv
uv run python manage.py migrate          # apply Django migrations
uv run python manage.py runserver        # dev server on :8000
uv run python manage.py createsuperuser  # admin access (no models registered yet)
```

There is no test suite (`camera/tests.py` is empty) and no linter configured.

## Architecture

**Request flow.** `camera_project/urls.py` wires every route to a function view in `camera/views.py`:

- `GET /` → `index` — control page (camera-type dropdown + start/stop buttons + `<img src="/video_stream/">`).
- `GET /start_camera/?camera_type={internal|usb|default}` → `start_camera` — opens a `cv2.VideoCapture` and stores it in a module global.
- `GET /stop_camera/` → `stop_camera` — releases all camera globals.
- `GET /video_stream/` → `video_stream_view` — returns a `StreamingHttpResponse` of `multipart/x-mixed-replace` JPEG frames produced by the `video_stream()` generator.
- `GET /livestream/` → `livestream` — bare page that just embeds the stream.
- `GET /history/` → `video_history` — lists files in `VIDEOS_DIR` and renders them with `<video>` tags.

**Camera state is process-global.** `views.py` holds three module-level `cv2.VideoCapture` handles (`internal_camera`, `external_camera`, `camera`). `start_camera` releases all three, then opens one based on `camera_type`. The `video_stream()` generator iterates over `[internal_camera, external_camera, camera]` each frame and uses the first that's open. This design assumes one Django worker process and one viewer — concurrent requests, multiple workers (gunicorn `--workers >1`), or ASGI will break it.

**`usb` camera detection.** `find_external_camera()` brute-forces indices 1–99 calling `cv2.VideoCapture(idx)` until one opens. This is slow on first call and is the documented way to pick a USB camera (no UI for choosing a specific index).

**Recording pipeline inside `video_stream()`.** Every 15 s wall-clock the generator:

1. Releases the current `cv2.VideoWriter` (which has been writing `videos/video_{N}.mp4` with the `mp4v` fourcc).
2. Spawns a *blocking* `subprocess.run(['ffmpeg', ...], check=True)` to re-encode that file to `videos/video_{N}_h264.mp4` with libx264/AAC.
3. Deletes the original `mp4v` file.
4. Opens a new `VideoWriter` for the next segment.

Because the ffmpeg call runs synchronously inside the streaming generator, the MJPEG stream **stalls** for the duration of the encode. Any change to the recorder should preserve frame-pump cadence (move encoding to a thread/queue, Celery, or a post-process task).

**Storage layout.** `settings.py` sets `MEDIA_ROOT = BASE_DIR / 'videos'` and `VIDEOS_DIR = BASE_DIR / 'videos'` — same directory, two names. `MEDIA_URL = 'media/'`, and `urls.py` appends `static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)` so `videos/foo.mp4` is served at `/media/foo.mp4`. `video_history` builds URLs as `os.path.join(MEDIA_URL, 'videos', filename)` — note the extra `videos/` segment, which does not match `MEDIA_ROOT`'s actual layout. There's also an unused empty `media/videos/` directory at the repo root.

**Settings caveats (dev defaults, do not ship).** `SECRET_KEY` is hardcoded, `DEBUG = True`, `ALLOWED_HOSTS = []`, and `settings.py` has a stray `print(MEDIA_ROOT)` at import time. `csrf` middleware is enabled but the JS `fetch('/start_camera/')` calls are GETs, so CSRF doesn't bite — switching them to POST will require a token.

## Things to know before editing

- Don't add features that assume multiple workers, async views, or multiple simultaneous viewers without first replacing the module-global camera handles — the current design cannot support them.
- The `video_stream()` generator never exits cleanly (the `if video_writer: video_writer.release()` after the `while True:` is dead code). When the client disconnects, the generator is GC'd mid-segment and the in-flight `mp4v` file is left behind un-encoded.
- `MEDIA_ROOT` vs `VIDEOS_DIR` vs `media/videos/` is currently inconsistent — fixing recording/playback paths means fixing all three together.
- The repo contains a stray top-level `hello.py` (uv-template scaffold) and an empty `README.md`; neither is wired into anything.
