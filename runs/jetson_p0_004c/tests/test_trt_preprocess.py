import unittest
import numpy as np
from src.contracts import DetectorError


class PreprocessTests(unittest.TestCase):
    def check_geometry(self, shape, resized, padding):
        from src.vision.tensorrt_preprocess import preprocess
        image=np.full((*shape,3),[10,20,30],dtype=np.uint8)
        original=image.copy()
        output, transform=preprocess(image,'float32')
        self.assertEqual(output.shape,(1,3,640,640))
        self.assertEqual(output.dtype,np.float32)
        self.assertTrue(output.flags.c_contiguous)
        self.assertEqual(transform.original_shape,shape)
        self.assertEqual(transform.resized_shape,resized)
        self.assertEqual(transform.padding,padding)
        left,top,_,_=padding
        np.testing.assert_allclose(output[0,:,top,left],[30/255,20/255,10/255])
        if top:np.testing.assert_allclose(output[0,:,0,0],np.full(3,114/255))
        np.testing.assert_array_equal(image,original)

    def test_landscape(self):self.check_geometry((720,1280),(360,640),(0,140,0,140))
    def test_portrait(self):self.check_geometry((1280,720),(640,360),(140,0,140,0))
    def test_square_scaleup(self):self.check_geometry((10,10),(640,640),(0,0,0,0))
    def test_odd_rounding_split(self):self.check_geometry((333,500),(426,640),(0,107,0,107))
    def test_asymmetric_padding(self):self.check_geometry((335,500),(429,640),(0,105,0,106))

    def test_declared_fp16_and_noncontiguous_input(self):
        from src.vision.tensorrt_preprocess import preprocess
        source=np.full((640,1280,3),[0,128,255],dtype=np.uint8)[:,::2,:]
        tensor,_=preprocess(source,'float16')
        self.assertTrue(tensor.flags.c_contiguous)
        self.assertEqual(tensor.dtype,np.float16)
        np.testing.assert_array_equal(tensor[0,:,0,0],np.array([255,128,0],np.float16)/255)

    def test_invalid_images_and_dtype(self):
        from src.vision.tensorrt_preprocess import preprocess
        for image in [None,[[[0,0,0]]],np.zeros((3,3)),np.zeros((3,3,4),np.uint8),
                      np.zeros((0,3,3),np.uint8),np.zeros((3,3,3),np.float32)]:
            with self.subTest(image_type=type(image).__name__):
                with self.assertRaisesRegex(DetectorError,'INPUT_CONTRACT_MISMATCH'):
                    preprocess(image,'float32')
        with self.assertRaisesRegex(DetectorError,'INPUT_CONTRACT_MISMATCH'):
            preprocess(np.zeros((3,3,3),np.uint8),'int8')
