"""Custom pet images with local U2NETP semantic foreground segmentation.

Inference uses the ONNX model published by rembg, with the model's RGB
normalization and soft foreground mask. No photos are uploaded. Dependencies
and the model are optional explicit installs; image import never downloads.
An explicit flat mode remains for illustrations; automatic mode always uses AI.
Semantic masks never restore source opacity, but may trim existing cutouts further.
Disable background removal to preserve an existing cutout exactly (apart from
bounded scaling and cropping transparent margins).
"""
from collections import Counter, deque
from dataclasses import dataclass
from pathlib import Path
import os
import tempfile
import sys
import threading
import importlib.util
import urllib.request

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QImageReader

MAX_SOURCE_PIXELS = 24_000_000
MAX_SOURCE_BYTES = 32 * 1024 * 1024
MAX_PET_SIZE = 1024
CUSTOM_FILENAME = "custom-pet.png"
MODEL_URL = "https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2netp.onnx"
MODEL_FILENAME = "u2netp.onnx"
_SESSION = None
_SESSION_PATH = None
_SESSION_LOCK = threading.Lock()


def background_model_path(data_dir):
    """Resolve an explicit installation before the per-user app model cache."""
    installed = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)) / "models" / MODEL_FILENAME
    return installed if installed.is_file() else Path(data_dir) / "cache" / "background" / MODEL_FILENAME


def background_removal_status(data_dir):
    if any(importlib.util.find_spec(name) is None for name in ("numpy", "onnxruntime")):
        return False, "AI removal needs its optional runtime. Run ./enable-background-removal.sh in the project folder."
    if not background_model_path(data_dir).is_file():
        return False, "AI foreground model is missing. Run ./enable-background-removal.sh once; subsequent image imports work offline."
    return True, "Local AI foreground detection ready (U2NETP / CPU)."


def download_background_model(data_dir=None, *, model_dir=None):
    """Explicit setup only: bounded HTTPS model download to an atomic file."""
    if model_dir is None:
        if data_dir is None:
            raise ValueError("Provide an app data directory or a model directory.")
        model_dir = Path(data_dir) / "cache" / "background"
    directory = Path(model_dir)
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / MODEL_FILENAME
    if destination.is_file():
        return destination
    fd, name = tempfile.mkstemp(prefix=".model-", suffix=".onnx", dir=directory)
    total = 0
    try:
        with os.fdopen(fd, "wb") as output, urllib.request.urlopen(MODEL_URL, timeout=45) as response:
            while chunk := response.read(64 * 1024):
                total += len(chunk)
                if total > 10 * 1024 * 1024:
                    raise ValueError("The downloaded model exceeds its expected size.")
                output.write(chunk)
        if total < 1024 * 1024:
            raise ValueError("The model download is incomplete. Try setup again.")
        # Parse before installing: failed/corrupt downloads never replace a model.
        import onnxruntime as ort
        ort.disable_telemetry_events()
        options = ort.SessionOptions()
        options.intra_op_num_threads = 1
        check = ort.InferenceSession(name, sess_options=options, providers=["CPUExecutionProvider"])
        del check
        os.replace(name, destination)
    finally:
        Path(name).unlink(missing_ok=True)
    return destination


def _semantic_session(data_dir):
    global _SESSION, _SESSION_PATH
    ready, message = background_removal_status(data_dir)
    if not ready:
        raise ValueError(message)
    import onnxruntime as ort
    ort.disable_telemetry_events()
    path = background_model_path(data_dir).resolve()
    with _SESSION_LOCK:
        if _SESSION is None or _SESSION_PATH != path:
            options = ort.SessionOptions()
            options.intra_op_num_threads = 2
            options.inter_op_num_threads = 1
            options.log_severity_level = 3
            try:
                _SESSION = ort.InferenceSession(str(path), sess_options=options,
                    providers=["CPUExecutionProvider"])
                _SESSION_PATH = path
            except Exception as error:
                raise ValueError("The AI model cannot be loaded. Remove its cached file and run background setup again.") from error
        return _SESSION


def _apply_foreground_mask(image, alpha):
    """Semantic masking can remove pixels but cannot restore source opacity."""
    import numpy as np
    rgba = np.frombuffer(image.constBits(), dtype=np.uint8).reshape(image.height(), image.width(), 4).copy()
    rgba[:, :, 3] = np.minimum(rgba[:, :, 3], alpha)
    return QImage(rgba.data, image.width(), image.height(), image.width() * 4,
                  QImage.Format.Format_RGBA8888).copy()


def _remove_semantic_background(image, data_dir):
    import numpy as np
    session = _semantic_session(data_dir)
    scaled = image.scaled(320, 320, Qt.AspectRatioMode.IgnoreAspectRatio,
                          Qt.TransformationMode.SmoothTransformation)
    rgb = np.frombuffer(scaled.constBits(), dtype=np.uint8).reshape(320, 320, 4)[:, :, :3].astype(np.float32)
    rgb /= max(float(rgb.max()), 1e-6)
    rgb = (rgb - np.asarray([.485, .456, .406], dtype=np.float32)) / np.asarray([.229, .224, .225], dtype=np.float32)
    tensor = np.ascontiguousarray(rgb.transpose(2, 0, 1)[None], dtype=np.float32)
    try:
        prediction = session.run(None, {session.get_inputs()[0].name: tensor})[0][0, 0]
    except Exception as error:
        raise ValueError("AI foreground detection failed. Try another image or keep its background.") from error
    low, high = float(prediction.min()), float(prediction.max())
    if not np.isfinite(prediction).all() or high - low <= 1e-6:
        raise ValueError("AI could not identify a foreground subject. Choose another image or keep its background.")
    mask = np.clip((prediction - low) * (255.0 / (high - low)), 0, 255).astype(np.uint8)
    small_mask = QImage(mask.data, 320, 320, 320, QImage.Format.Format_Grayscale8).copy()
    large_mask = small_mask.scaled(image.width(), image.height(), Qt.AspectRatioMode.IgnoreAspectRatio,
                                  Qt.TransformationMode.SmoothTransformation)
    # Grayscale scanlines have Qt padding when the width is not divisible by 4.
    alpha = np.frombuffer(large_mask.constBits(), dtype=np.uint8).reshape(image.height(), large_mask.bytesPerLine())[:, :image.width()].copy()
    alpha[alpha < 8] = 0
    alpha[alpha > 247] = 255
    visible = float(np.mean(alpha > 127))
    transparent = float(np.mean(alpha < 128))
    if visible < .002 or transparent < .002:
        raise ValueError("AI did not produce a usable subject cutout. Choose another image or keep its background.")
    result = _apply_foreground_mask(image, alpha)
    return result, True, "AI subject detected locally; photo background removed. Check the preview for fine details.", transparent



@dataclass(frozen=True)
class ImportResult:
    path: Path
    background_removed: bool
    message: str
    removed_fraction: float = 0.0


def custom_pet_path(data_dir):
    return Path(data_dir) / CUSTOM_FILENAME


def _decode(source):
    source = Path(source)
    if source.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
        raise ValueError("Choose a PNG, JPG or JPEG image.")
    try:
        size_bytes = source.stat().st_size
    except OSError as exc:
        raise ValueError("The image cannot be read.") from exc
    if size_bytes > MAX_SOURCE_BYTES:
        raise ValueError("Choose an image smaller than 32 MB.")
    reader = QImageReader(str(source))
    reader.setAutoTransform(True)
    if bytes(reader.format()).lower() not in {b"png", b"jpeg", b"jpg"}:
        raise ValueError("The file is not a valid PNG or JPEG image.")
    size = reader.size()
    if not size.isValid() or size.width() * size.height() > MAX_SOURCE_PIXELS:
        raise ValueError("Choose an image with at most 24 million pixels.")
    image = reader.read()
    if image.isNull():
        raise ValueError("The image is damaged or cannot be decoded.")
    if max(image.width(), image.height()) > MAX_PET_SIZE:
        image = image.scaled(MAX_PET_SIZE, MAX_PET_SIZE,
                             Qt.AspectRatioMode.KeepAspectRatio,
                             Qt.TransformationMode.SmoothTransformation)
    return image.convertToFormat(QImage.Format.Format_RGBA8888)


def _pixels(image):
    # RGBA8888 has four bytes per pixel and no padding for any image width.
    return bytearray(image.constBits())


def _remove_flat_background(image, tolerance):
    pixels = _pixels(image)
    width, height = image.width(), image.height()
    count = width * height
    if any(pixels[i] < 255 for i in range(3, len(pixels), 4)):
        return image, False, "Existing transparency preserved.", 0.0
    # Sample all edges; quantization tolerates JPEG noise without selecting
    # foreground colours independently at each corner.
    edges = list(range(width)) + list(range((height - 1) * width, count))
    edges += [y * width for y in range(1, height - 1)]
    edges += [y * width + width - 1 for y in range(1, height - 1)]
    bins = Counter(tuple(pixels[4 * i + c] // 32 for c in range(3)) for i in edges)
    key, _ = bins.most_common(1)[0]
    group = [i for i in edges if tuple(pixels[4 * i + c] // 32 for c in range(3)) == key]
    color = tuple(sum(pixels[4 * i + c] for i in group) // len(group) for c in range(3))

    def matches(i):
        return max(abs(pixels[4 * i + c] - color[c]) for c in range(3)) <= tolerance

    seeds = [i for i in edges if matches(i)]
    if len(seeds) / len(edges) < .60:
        return image, False, "Complex background kept. Use an image with transparency or a plain background for automatic removal.", 0.0
    visited = bytearray(count)
    queue = deque()
    for i in seeds:
        if not visited[i]:
            visited[i] = 1
            queue.append(i)
    while queue:
        i = queue.popleft()
        x = i % width
        neighbours = []
        if x:
            neighbours.append(i - 1)
        if x < width - 1:
            neighbours.append(i + 1)
        if i >= width:
            neighbours.append(i - width)
        if i < count - width:
            neighbours.append(i + width)
        for j in neighbours:
            if not visited[j] and matches(j):
                visited[j] = 1
                queue.append(j)
    removed = sum(visited)
    if removed >= count * .995:
        raise ValueError("No visible pet remains after removing the background. Disable background removal or choose another image.")
    for i, matched in enumerate(visited):
        if matched:
            pixels[4 * i + 3] = 0
    result = QImage(pixels, width, height, width * 4, QImage.Format.Format_RGBA8888).copy()
    return result, bool(removed), "Plain background removed; enclosed details preserved.", removed / count


def _crop_visible(image):
    pixels = _pixels(image)
    width, height = image.width(), image.height()
    left, top, right, bottom = width, height, -1, -1
    for y in range(height):
        row = y * width
        for x in range(width):
            if pixels[4 * (row + x) + 3]:
                left, top = min(left, x), min(top, y)
                right, bottom = max(right, x), max(bottom, y)
    if right < 0:
        raise ValueError("The image is fully transparent. Choose an image with a visible pet.")
    return image.copy(left, top, right - left + 1, bottom - top + 1)


def import_pet_image(source_path, data_dir, *, remove_background=True, tolerance=36, background_mode="semantic"):
    """Decode, optionally segment the foreground, crop, and atomically save.

    A failed import leaves the existing pet untouched. Persist only our own PNG
    filename; imported paths never become settings paths or executable content.
    """
    if isinstance(tolerance, bool) or not isinstance(tolerance, (int, float)) or not 0 <= tolerance <= 100:
        raise ValueError("Background tolerance must be between 0 and 100.")
    if background_mode not in {"semantic", "flat"}:
        raise ValueError("Choose semantic or flat background removal.")
    image = _decode(source_path)
    removed, message, fraction = False, "Background kept.", 0.0
    if remove_background:
        if background_mode == "flat":
            image, removed, message, fraction = _remove_flat_background(image, tolerance)
        else:
            ready, message = background_removal_status(data_dir)
            if not ready:
                raise ValueError(message)
            image, removed, message, fraction = _remove_semantic_background(image, data_dir)
    image = _crop_visible(image)
    destination = custom_pet_path(data_dir)
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".pet-import-", suffix=".png", dir=destination.parent)
    os.close(fd)
    try:
        if not image.save(name, "PNG"):
            raise ValueError("The imported pet could not be saved.")
        os.replace(name, destination)
    finally:
        Path(name).unlink(missing_ok=True)
    return ImportResult(destination, removed, message, fraction)


def load_custom_pet_image(data_dir):
    """Return a bounded custom image, or None when absent/corrupt."""
    path = custom_pet_path(data_dir)
    if not path.is_file():
        return None
    try:
        return _crop_visible(_decode(path))
    except (ValueError, OSError):
        return None


def reset_pet_image(data_dir):
    """Remove the user's imported PNG; the UI then restores its bundled sprite."""
    custom_pet_path(data_dir).unlink(missing_ok=True)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Install the local U2NETP foreground model once.")
    parser.add_argument("--download-model", action="store_true", required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--data-dir", type=Path)
    group.add_argument("--model-dir", type=Path)
    args = parser.parse_args()
    try:
        print(download_background_model(args.data_dir, model_dir=args.model_dir))
    except Exception as error:
        parser.exit(1, f"Background model setup failed: {error}\n")
