"""Offline custom pet imports. Qt's image decoder is also used by the desktop app.

Automatic removal targets a nearly uniform background connected to image edges.
Complex photographic backgrounds are kept: reliable semantic removal needs a model.
This module uses QImage only, so importing is safe in a worker thread.
"""
from collections import Counter, deque
from dataclasses import dataclass
from pathlib import Path
import os
import tempfile

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QImageReader

MAX_SOURCE_PIXELS = 24_000_000
MAX_SOURCE_BYTES = 32 * 1024 * 1024
MAX_PET_SIZE = 1024
CUSTOM_FILENAME = "custom-pet.png"


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


def import_pet_image(source_path, data_dir, *, remove_background=True, tolerance=36):
    """Decode, optionally remove a flat background, crop, and atomically save.

    A failed import leaves the existing pet untouched. Persist only our own PNG
    filename; imported paths never become settings paths or executable content.
    """
    if isinstance(tolerance, bool) or not isinstance(tolerance, (int, float)) or not 0 <= tolerance <= 100:
        raise ValueError("Background tolerance must be between 0 and 100.")
    image = _decode(source_path)
    removed, message, fraction = False, "Background kept.", 0.0
    if remove_background:
        image, removed, message, fraction = _remove_flat_background(image, tolerance)
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
