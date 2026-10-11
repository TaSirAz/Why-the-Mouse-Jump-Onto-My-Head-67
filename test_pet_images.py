"""Image import regressions: subject preservation and safe replacement."""
from pathlib import Path
import tempfile
import unittest
import importlib.util
from unittest.mock import patch

from PySide6.QtGui import QColor, QImage
from pet_images import import_pet_image, load_custom_pet_image, reset_pet_image, _apply_foreground_mask


class PetImageTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.data = self.root / 'data'

    def tearDown(self):
        self.directory.cleanup()

    def image(self, name='source.png', alpha=False):
        image = QImage(40, 40, QImage.Format.Format_RGBA8888)
        image.fill(QColor('white'))
        for y in range(10, 30):
            for x in range(10, 30):
                image.setPixelColor(x, y, QColor('black'))
        image.setPixelColor(20, 20, QColor('white'))  # enclosed foreground detail
        if alpha:
            for y in range(10):
                for x in range(40):
                    image.setPixelColor(x, y, QColor(10, 20, 30, 0))
            image.setPixelColor(0, 0, QColor(10, 20, 30, 60))
        source = self.root / name
        self.assertTrue(image.save(str(source)))
        return source

    def test_edge_connected_removal_crops_but_preserves_enclosed_detail(self):
        result = import_pet_image(self.image(), self.data, background_mode="flat")
        image = load_custom_pet_image(self.data)
        self.assertTrue(result.background_removed)
        self.assertEqual((image.width(), image.height()), (20, 20))
        self.assertEqual(image.pixelColor(10, 10), QColor('white'))
        reset_pet_image(self.data)
        self.assertIsNone(load_custom_pet_image(self.data))

    def test_existing_alpha_is_preserved(self):
        result = import_pet_image(self.image(alpha=True), self.data, remove_background=False)
        self.assertFalse(result.background_removed)
        self.assertEqual(load_custom_pet_image(self.data).pixelColor(0, 0).alpha(), 60)

    def test_jpeg_import_and_explicit_background_keep(self):
        result = import_pet_image(self.image('source.JPG'), self.data, remove_background=False)
        self.assertFalse(result.background_removed)
        self.assertEqual(load_custom_pet_image(self.data).width(), 40)
        self.assertEqual(result.path.suffix, '.png')

    def test_failed_import_keeps_previous_pet(self):
        result = import_pet_image(self.image(), self.data, background_mode="flat")
        old = result.path.read_bytes()
        corrupt = self.root / 'broken.png'
        corrupt.write_text('not an image')
        with self.assertRaises(ValueError):
            import_pet_image(corrupt, self.data)
        self.assertEqual(result.path.read_bytes(), old)
        blank = QImage(20, 20, QImage.Format.Format_RGBA8888)
        blank.fill(QColor('white'))
        blank.save(str(self.root / 'blank.png'))
        with self.assertRaisesRegex(ValueError, 'No visible pet'):
            import_pet_image(self.root / 'blank.png', self.data, background_mode="flat")
        self.assertEqual(result.path.read_bytes(), old)

    def test_default_ai_unavailable_does_not_fall_back_or_replace(self):
        prior = import_pet_image(self.image(), self.data, background_mode="flat").path.read_bytes()
        with patch("pet_images.background_removal_status", return_value=(False, "Install AI runtime")):
            with self.assertRaisesRegex(ValueError, "Install AI runtime"):
                import_pet_image(self.image(), self.data)
        self.assertEqual((self.data / 'custom-pet.png').read_bytes(), prior)

    def test_incidental_alpha_does_not_bypass_semantic_detection(self):
        source = self.image()
        image = QImage(str(source)).convertToFormat(QImage.Format.Format_RGBA8888)
        image.setPixelColor(0, 0, QColor(255, 255, 255, 60))
        image.save(str(source))
        with patch('pet_images.background_removal_status', return_value=(True, 'ready')), patch(
                'pet_images._remove_semantic_background', return_value=(image, True, 'AI', .5)) as segment:
            result = import_pet_image(source, self.data)
        segment.assert_called_once()
        self.assertTrue(result.background_removed)

    def test_transparent_frame_does_not_bypass_semantic_detection(self):
        source = self.image(alpha=True)
        image = QImage(str(source)).convertToFormat(QImage.Format.Format_RGBA8888)
        with patch('pet_images.background_removal_status', return_value=(True, 'ready')), patch(
                'pet_images._remove_semantic_background', return_value=(image, True, 'AI', .5)) as segment:
            result = import_pet_image(source, self.data)
        segment.assert_called_once()
        self.assertTrue(result.background_removed)

    @unittest.skipUnless(importlib.util.find_spec('numpy'), 'Optional AI runtime is not installed')
    def test_semantic_mask_cannot_restore_partial_source_opacity(self):
        import numpy as np
        image = QImage(3, 1, QImage.Format.Format_RGBA8888)
        image.fill(QColor('black'))
        image.setPixelColor(0, 0, QColor(0, 0, 0, 60))
        image.setPixelColor(1, 0, QColor(0, 0, 0, 0))
        result = _apply_foreground_mask(image, np.asarray([[255, 255, 70]], dtype=np.uint8))
        self.assertEqual([result.pixelColor(x, 0).alpha() for x in range(3)], [60, 0, 70])

    def test_complex_edges_do_not_trigger_removal(self):
        image = QImage(40, 40, QImage.Format.Format_RGBA8888)
        for y in range(40):
            for x in range(40):
                image.setPixelColor(x, y, QColor((x * 11) % 256, (y * 13) % 256, ((x + y) * 17) % 256))
        source = self.root / 'photo.png'
        image.save(str(source))
        result = import_pet_image(source, self.data, background_mode="flat")
        self.assertFalse(result.background_removed)
        self.assertIn('Complex background', result.message)


if __name__ == '__main__':
    unittest.main()
