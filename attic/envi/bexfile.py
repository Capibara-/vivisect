'''
Unified binary executable file format module.
'''
from envi.const import *
class implement(Exception):pass

class BexFile:
    '''
    An object which implements the concepts common to most
    executable file formats.  Individual formats will extend
    this object and may implement additional APIs which should
    begin with the format name ( ie, peGetResources ).
    '''

    def __init__(self, fd):
        self.fd = fd
        self.info = {}
        self.cache = {}

    def entry(self):
        '''
        Return the rva of the entry point (or None).
        '''
        self._get_cache(self._bex_entry)

    def baseaddr(self):
        """
        Return the suggested base address from the executable file.
        ( or None if not present )
        """
        self._get_cache(self._bex_baseaddr)

    def relocs(self):
        '''
        Retrieve a list of the relocation tuples for the executable file.
        Each reloc is returned as a tuple of ( rva, rsize, rtype ) where rtype
        is one of the RELOC_ constants defined in envi/const.py

        Example:
            for rva,rsize,rtype in bex.relocs():
                print("reloc at rva: 0x%.8x" % rva)
        '''
        return self._get_cache(self._bex_relocs)

    def memmaps(self):
        """
        Return a list of (rva,size,perms,off) tuples for
        the memory maps defined in the executable file.  If the memory
        map is defined within the file, off is the offset within the
        file ( otherwise None )
        """
        return self._get_cache(self._bex_memmaps)

    def symbols(self):
        """
        Return a list of (rva,size,name,symtype) tuples for the
        symbols defined in the executable file.  Symtype will be
        one of the SYM_ constants defined in envi/const.py
        """
        return self._get_cache(self._bex_symbols)

    def sections(self):
        """
        Return a list of (rva,size,name) section tuples for the
        sections defined in the executable file.

        Example:
            for rva,size,name in b.sections():
                print("section rva: 0x%.8x (%s)" % (rva,name))

        NOTE: "sections" are seperated from "memory maps" in the
              BexFile API to account for formats which define them
              differently.  In many instances, they may be equivalent.
        """
        return self._get_cache(self._bex_sections)

    def section(self, name):
        """
        Return the section tuple (rva,size,name) or None for a section by name.

        Example:
            sectup = bex.section('.text')
            if sectup != None:
                print("has .text section!")
        """
        for sec in self.sections():
            if sec[2] == name:
                return sec

    def struct(self, vsclass, rva=None, off=None, fast=False):
        """
        Instantiate a vstruct class and optionally parse from the
        specified offset or rva.
        """
        vs = vsclass()
        size = len(vs)
        if rva != None:
            vs.vsParse(self.readrva(rva, size), fast=fast)
            return vs
        if off != None:
            vs.vsParse(self.readoff(off, size), fast=fast)
            return vs
        return vs

    def bintype(self):
        """
        Return a string representing the "type" of binary executable.
        The following types are valid:
            "exe"   - The file represents an exec-able process image
            "dyn"   - The file represents a dynamically loadable library.
            "unk"   - The file binary type is unknown (generally an error).

        For most purposes, embedded images such as firmware and bios
        should return "exe".

        Example:
            if bex.bintype() == "dyn":
                libstuff(bex)
        """
        return self._get_cache(self._bex_bintype)

    def _get_cache(self, ctor):
        #if not self.cache.has_key(name):
            #self.cache[name] = ctor()
        #return self.cache.get(name)
        if not self.cache.has_key(ctor):
            self.cache[ctor] = ctor()
        return self.cache.get(ctor)

    def rva2off(self, rva):
        """
        Translate from an rva to a file offset based on memmaps.
        """
        for addr,size,perms,off in self.memmaps():
            if off != None and rva >= addr and rva <= (addr + size):
                return off + (rva-addr)

    def off2rva(self, off):
        """
        Translate from a file offset to an rva based on memmaps.
        """
        for addr,size,perms,foff in self.memmaps():
            if foff != None and off >= foff and off <= (foff + size):
                return addr + (off - foff)

    def readrva(self, rva, size):

        off = self.rva2off(rva)
        if off == None:
            return None

        self.fd.seek(off)
        return self.fd.read(size)

    def readoff(self, off, size):

        self.fd.seek(off)
        return self.fd.read(size)

    def _bex_entry(self): return None
    def _bex_bintype(self): raise implement('_bex_bintype')
    def _bex_baseaddr(self): return None

    def _bex_relocs(self): return []
    def _bex_memmaps(self): return []
    def _bex_symbols(self): return []
    def _bex_sections(self): return []

