import unittest
from mock import MagicMock, patch
from PIL import Image
import server_image
import io

class TestServerImage(unittest.TestCase):

    def test_resize_image(self):
        img = Image.new('RGB', (1000, 500), 'white')
        resized = server_image.resize_image(img, 384)
        self.assertEqual(resized.size[0], 384)
        self.assertEqual(resized.size[1], 192)

    def test_grayscale(self):
        # Create a red image
        img = Image.new('RGBA', (100, 100), (255, 0, 0, 255))
        gray = server_image.to_grayscale(img)
        self.assertEqual(gray.mode, 'L')
        # Red in grayscale (ITU-R 601-2) is roughly 0.299*R ~ 76
        # Our implementation uses Pillow's L conversion which is similar.
        # Let's check pixel value is not 0 (black) or 255 (white)
        self.assertTrue(0 < gray.getpixel((0,0)) < 255)
        
    def test_pack_to_pbm(self):
        # 2x2 checkerboard
        img = Image.new('1', (8, 1), 0) # 8 width, 1 height. All black (0)
        # Wait, in Pillow '1', 0 is Black. PBM P4 1 is Black.
        # server_image.pack_to_pbm inverts L before converting to 1?
        # No, I checked my implementation, I am essentially converting L->1.
        # Let's verify what pack_to_pbm produces.
        
        # Test specific known input
        # White image
        img_white = Image.new('RGB', (8, 1), 'white') 
        img_gray = server_image.to_grayscale(img_white)
        pbm = server_image.pack_to_pbm(img_gray)
        
        header, data = pbm.split(b'\n', 2)[0:2], pbm.split(b'\n', 2)[2]
        self.assertEqual(header[0], b'P4')
        self.assertEqual(header[1], b'8 1')
        
        # White in PBM is 0. 
        # data should be \x00
        self.assertEqual(data, b'\x00')
        
        # Black image
        img_black = Image.new('RGB', (8, 1), 'black') 
        img_gray_b = server_image.to_grayscale(img_black)
        pbm_b = server_image.pack_to_pbm(img_gray_b)
        # Black in PBM is 1.
        # data should be \xff (11111111)
        self.assertEqual(pbm_b.split(b'\n', 2)[2], b'\xff')

if __name__ == '__main__':
    unittest.main()
