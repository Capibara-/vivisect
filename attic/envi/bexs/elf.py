import vstruct
import envi.bexfile as e_bexfile
import vstruct.defs.elf as vs_elf

from envi.const import *

# TEMPORARY
import Elf

elf_bintypes = {
    Elf.ET_DYN:"dyn",
    Elf.ET_EXEC:"exe",
}

class ElfFile(e_bexfile.BexFile):

    def __init__(self, fd):
        e_bexfile.BexFile.__init__(self, fd)
        elf = self.elfHeader()

    def elfHeader(self):
        return self._get_cache(self._elf_elfhdr)

    def elfIsPreLinked(self):
        '''
        Returns True if the Elf binary is prelinked.
        '''
        return self._get_cache(self._elf_prelinked)

    def _elf_prelinked(self):
        for dyn in self.elfDynSyms():
            if dyn.d_tag == Elf.DT_GNU_PRELINKED:
                return True
            if dyn.d_tag == Elf.DT_GNU_CONFLICTSZ:
                return True
        return False

    def elfDynSyms(self):
        """
        Return a list of the ElfDynamic vstructs for the .dynamic section.
        """
        return self._get_cache(self._elf_dynsyms)

    def _elf_dynsyms(self):
        sectup = self.section(".dynamic")
        if sectup == None:
            return []

        addr,size,name = sectup

        hdr = self.elfHeader()
        dynlen = len(hdr._elf_dynamic())

        ret = []
        maxaddr = addr + size
        while addr < maxaddr:
            dyn = hdr._elf_dynamic()
            buf = self.readrva(addr,dynlen)
            if not buf:
                print("short readrva() for .dynamic")
                break

            dyn.vsParse(buf)
            ret.append(dyn)
            addr += dynlen
        return ret

    def _bex_baseaddr(self):
        if self.bintype() == "dyn" and not self.elfIsPreLinked():
            return None

        addrs = [ p.p_vaddr for p in self.elfPheaders() if p.p_vaddr != 0 ]
        return min(addrs)

    def _bex_bintype(self):
        elftype = self.elfHeader().e_type
        return elf_bintypes.get(elftype,"unk")

    def _elf_elfhdr(self):
        elf = vs_elf.Elf32()
        hdrbytes = self._elf_readhdr(0,vs_elf.elfsize)

        elf.vsParse(hdrbytes)
        if elf.e_machine in Elf.e_machine_64:
            elf = vs_elf.Elf64()
            elf.vsParse(hdrbytes)

        return elf

    def _bex_iterstruct_rva(self, rva, size, cls):
        maxva = rva + size
        while rva < maxva:
            s = cls()
            l = len(s)
            b = self.readrva(rva,l)
            s.vsParse(b)
            yield s
            rva += l

    def _bex_sections(self):
        elf = self.elfHeader()
        if not elf.e_shoff:
            return []

        #sec = elf._elf_section()
        #secbytes = self.readoff(elf.e_shoff, elf.e_shnum * elf.e_shentsize )
        secbytes = self._elf_readhdr(elf.e_shoff, elf.e_shnum * elf.e_shentsize )

        secs = [ sec for (off,sec) in elf._elf_section.iterbytes(secbytes) ]

        # Populate the section names
        strsec = secs[elf.e_shstrndx]
        names = self.readoff(strsec.sh_offset,strsec.sh_size)

        ret = []
        for sec in secs:
            if sec.sh_addr == 0:
                continue
            name = names[sec.sh_name:].split("\x00")[0]
            ret.append( (sec.sh_addr, sec.sh_size, name or None) )

        return ret

    def _bex_symbols(self):
        ret = []
        for secva,secsize,secname in self.sections():
            ret.append( ( secva, secsize, secname, SYM_SECTION) )
        return ret

    def elfPheaders(self):
        """
        Returns a list of ElfPHeader vstructs.
        """
        return self._get_cache(self._elf_pheaders)

    def _elf_readhdr(self, off, size):
        # since rva == offset for the first map...
        self.fd.seek(off)
        return self.fd.read(size)

    def _elf_pheaders(self):
        elf = self.elfHeader()
        if not elf.e_phoff:
            return []

        phdrbytes = self._elf_readhdr(elf.e_phoff, elf.e_phentsize * elf.e_phnum)
        phdrs = [ phdr for (off,phdr) in elf._elf_pheader.iterbytes(phdrbytes) ]
        return phdrs

    def _bex_memmaps(self):
        ret = []
        for phdr in self.elfPheaders():
            if phdr.p_type != Elf.PT_LOAD:
                continue

            ret.append( (phdr.p_vaddr, phdr.p_memsz, phdr.p_flags & 0x7, phdr.p_offset) )

        print 'MAPS',repr(ret)
        return ret

if __name__ == '__main__':
    import sys
    elf = ElfFile(file(sys.argv[1],'rb'),inmem=False)
    print 'MAPS',elf.memmaps()
    print repr(elf.sections())
