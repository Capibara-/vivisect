import unittest
import vivisect.lib.bits as v_bits

class TestLibBits(unittest.TestCase):

    def test_libbits_masktest(self):
        val1 = int("101110100000",2)
        val2 = int("111110100000",2)
        tester = v_bits.masktest("1011xxxx0000")
        self.assertTrue( tester(val1) )
        self.assertFalse( tester(val2) )

    def test_libbits_h2b(self):
        self.assertEqual(v_bits.h2b("41414141"),b"AAAA")

    def test_libbits_b2h(self):
        self.assertEqual(v_bits.b2h(b"AAAA"),"41414141")
