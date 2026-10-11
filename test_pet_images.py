"""Image import regressions: subject preservation and safe replacement."""
from pathlib import Path
import tempfile
import unittest

from PySide6.QtGui import QColor, QImage
from pet_images import import_pet_image, load_custom_pet_image, reset_pet_image


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
            image.setPixelColor(0, 0, QColor(10, 20, 30, 60))
        source = self.root / name
        self.assertTrue(image.save(str(source)))
        return source

    def test_edge_connected_removal_crops_but_preserves_enclosed_detail(self):
        result = import_pet_image(self.image(), self.data)
        image = load_custom_pet_image(self.data)
        self.assertTrue(result.background_removed)
        self.assertEqual((image.width(), image.height()), (20, 20))
        self.assertEqual(image.pixelColor(10, 10), QColor('white'))
        reset_pet_image(self.data)
        self.assertIsNone(load_custom_pet_image(self.data))

    def test_existing_alpha_is_preserved(self):
        result = import_pet_image(self.image(alpha=True), self.data)
        self.assertFalse(result.background_removed)
        self.assertEqual(load_custom_pet_image(self.data).pixelColor(0, 0).alpha(), 60)

    def test_jpeg_import_and_explicit_background_keep(self):
        result = import_pet_image(self.image('source.JPG'), self.data, remove_background=False)
        self.assertFalse(result.background_removed)
        self.assertEqual(load_custom_pet_image(self.data).width(), 40)
        self.assertEqual(result.path.suffix, '.png')

    def test_failed_import_keeps_previous_pet(self):
        result = import_pet_image(self.image(), self.data)
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
            import_pet_image(self.root / 'blank.png', self.data)
        self.assertEqual(result.path.read_bytes(), old)

    def test_complex_edges_do_not_trigger_removal(self):
        image = QImage(40, 40, QImage.Format.Format_RGBA8888)
        for y in range(40):
            for x in range(40):
                image.setPixelColor(x, y, QColor((x * 11) % 256, (y * 13) % 256, ((x + y) * 17) % 256))
        source = self.root / 'photo.png'
        image.save(str(source))
        result = import_pet_image(source, self.data)
        self.assertFalse(result.background_removed)
        self.assertIn('Complex background', result.message)


if __name__ == '__main__':
    unittest.main()
