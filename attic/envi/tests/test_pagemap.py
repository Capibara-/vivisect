import unittest

import envi.pagemap as e_pagemap

class TestPageMap(unittest.TestCase):

    def test_pagemap_pagemap(self):
        p = e_pagemap.PageMap(bits=12)
        p.put(0x41414141,4096,"A")
        self.assertEqual( p.get(0x41414141), "A" )
        self.assertEqual( p.get(0x41414000), "A" )
        self.assertEqual( p.get(0x41414fff), "A" )

        self.assertEqual( p.get(0x41413fff), None )
        self.assertEqual( p.get(0x41415000), None )

    def test_pagemap_pagelist(self):
        p = e_pagemap.PageList(bits=12)
        p.add(0x41414141,4096,"A")
        p.add(0x41414141,4096,"B")

        self.assertEqual( p.get(0x41414141), ["A","B"])
        self.assertEqual( p.get(0x41414000), ["A","B"])
        self.assertEqual( p.get(0x41414fff), ["A","B"])

        self.assertEqual( p.get(0x41413fff), [] )
        self.assertEqual( p.get(0x41415000), [] )
