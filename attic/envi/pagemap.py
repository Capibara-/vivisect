"""
A utility for doing sparse "page based" lookups.
"""
import collections

def pageiter(addr, size, bits):
    page = addr >> bits
    pagemax = ((addr + size) >> bits)
    return xrange(page,pagemax)

class PageMap:
    """
    Do page based lookup for a 1-to-1 mapping.
    """

    def __init__(self, bits=12):
        self._page_map = {}
        self._page_bits = bits

    def put(self, addr, size, val):
        """
        Set the given val as the object for the specified page range.

        Example:
            x = "HI"
            pm.set(0x41414141, 3333, x)
        """
        # SPEED HACK
        [ self._page_map.__setitem__(a,val) for a in pageiter(addr,size,self._page_bits) ]

    def get(self, addr):
        """
        Get the object previously stored for the given page addr.
        ( or None )

        Example:
            # if set with example from PageMapt.set()...
            print( pm.get(0x41414142) )
        """
        return self._page_map.get(addr >> self._page_bits)

    def pop(self, addr, size):
        """
        Remove the value from the given page range.
        """
        return [ self._page_map.pop(a,None) for a in pageiter(addr,size,self._page_bits) ]

class PageList:
    """
    Do page based lookup for a 1-to-many mapping.
    """
    def __init__(self, bits=12):
        self._page_map = collections.defaultdict(list)
        self._page_bits = bits

    def get(self, addr):
        """
        Get the list of objects added for the given page addr.
        """
        return self._page_map.get( addr >> self._page_bits, [])

    def add(self, addr, size, val):
        """
        Add the val to the page based lookup lists for given page range.
        """
        [ self._page_map[a].append(val) for a in pageiter(addr,size,self._page_bits) ]

    def rem(self, addr, size, val):
        """
        Del the val from the page based lookup lists for the given page range.
        """
        [ self._page_map.get(a).remove(val) for a in pageiter(addr,size,self._page_bits) ]
