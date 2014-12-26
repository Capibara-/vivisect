#import Elf

#import vtrace.formats.base as v_fmt_base
#import envi.symstore.resolver as e_resolv

#import envi.memory as e_mem
#import envi.bexs.elf as e_bx_elf

#class ElfTrace(v_fmt_base.TraceFormat):

    #def _fmt_init(self):
        #self.setMeta('format','elf')

    #def _plat_bexsyms(self, addr, size, name, path):

        #fd = self._plat_openfd(path,mode='rb')
        #if fd == None:
            # FIXME unitified print/event?
            #self.vprint('_plat_openfd() failed: %s' % path)
            #return

        #elf = e_bx_elf.ElfFile(fd)
        #return [ (a+addr,s,n,t) for (a,s,n,t) in elf.symbols() ]
