"""
Trace Platform Base
"""
# copyright (c) 2014 invisigoth - see LICENSE file for details
import traceback
import collections

import vtrace

import envi
import envi.memory as e_mem
import envi.threads as e_threads
import envi.symbols as e_symbols

#import envi.symstore.resolver as e_sym_resolv
#import envi.symstore.symcache as e_sym_symcache

import vstruct.builder as vs_builder

#def implementme(f):
    #def implme(*args, **kwargs):
        #clsname = args[0].__class__.__name__
        #methname = f.__name__
        #raise Exception('%s must implement %s' % (clsname,methname))
    #return implme

class TracePlatform:

    def _plat_init(self):
        pass

    def _plat_run(self): pass
    def _plat_break(self): pass

    def _plat_loadregs(self,tid,regs): pass
    def _plat_saveregs(self,tid,regs): pass
    def _plat_susthread(self,tid): pass
    def _plat_resthread(self,tid): pass

    def _plat_memmaps(self): pass
    def _plat_memread(self, addr, size): pass
    def _plat_memwrite(self, addr, bytez): pass
    def _plat_memalloc(self, size, perms=e_mem.MM_RWX, addr=None): pass
    def _plat_memprotect(self, addr, size, perms): pass

    def _plat_filecat(self, path): pass
    def _plat_fileopen(self, path): pass
    def _plat_fileread(self, fd, offset, size): pass
    def _plat_filewrite(self, fd, offset, bytez): pass

    def _plat_listdir(self, path): pass
    def _plat_readlink(self, path): pass

    def _plat_curbreak(self): pass
    def _plat_curwatch(self): pass

    #@implementme def _plat_readfile(self, path): pass    # readfile(path) -> bytes
    #@implementme def _plat_openfile(self, path): pass    # openfile(path) -> fd

    def _plat_openfd(self,path,mode='r+b'):
        return self.wire.openfd(path,mode)

    def _plat_libnorm(self, libpath):
        # do not use any os.path items here!
        basename = libpath.lower().replace("\\","/").split("/")[-1]
        return basename.split(".")[0].split("-")[0]

    def _plat_libsyms(self, libva, libsize, libnorm, libpath):
        return []

    def _plat_clear_breaks(self, breaks):
        for addr,info in breaks:
            self.writeMemory(addr,info['saved'])
            info['active'] = False

    def _plat_write_breaks(self, breaks):
        brk = self.archinfo['opdef']['brk']
        if brk == None:
            raise Exception('no archinfo brk for %s' % self.arch)

        size = len(brk)
        for addr,info in breaks:
            try:
                info['saved'] = self.readMemory(addr,size)
                self.writeMemory(va,brk)
            except Exception, e:
                info['enabled'] = False


class TraceBase(vtrace.Trace):

    def __init__(self, wire=None):

        vtrace.Trace.__init__(self, wire=wire)
        self.running = False
        self.exitcode = None
        self.runagain = False

        self.modes = {}
        self.modeinfo = {}
        self.autocont = set(['procinit','libinit','libfini','threadinit','threadexit','dbgprint'])

        self.breaks = {}
        self.signore = set()
        self.delaybreaks = []

        # A cache for memory maps, fd lists, regs, etc...
        self.cache = {}
        self.localvars = {}

        #self._break_after_bp = True     # Do we stop on the instruction *after* the bp?

        #self.symcache = None            # Set by setSymCachePath()
        #self.vsbuilder = vs_builder.VStructBuilder()

        self.hooks = {}
        self.hookdefs = {}
        self.hookpends = collections.deque()    # pended hook events (for next run())

        self.metadata = {}

        procinfo = {'pid':'process id'}
        self._hook_init('procinit',doc='fires on process attach',**procinfo)
        self._hook_init('procfini',doc='fires on process detach',**procinfo)
        self._hook_init('procexit',doc='fires on process exit',exitcode='exit code',**procinfo)

        siginfo = {'sig':'posix signal number'}
        self._hook_init('procsig',doc='fires when process is signaled',**siginfo)
        self._hook_init('proccont',doc='fires before process run',**siginfo)

        libinfo = {
            'va':'library base address',
            'norm':'normalized library name',
            'path':'raw filesystem path',
        }

        self._hook_init('libinit',doc='fires for library loads',**libinfo)
        self._hook_init('libfini',doc='fires for library unloads',**libinfo)

        thrinfo = {'tid':'thread id'}
        self._hook_init('threadinit',doc='fires on thread attach/create',**thrinfo)
        self._hook_init('threadfini',doc='fires on thread detach',**thrinfo)
        self._hook_init('threadexit',doc='fires on thread exit',exitcode='exit code',**thrinfo)

        self.libsbyva = {}
        self.libsbynorm = {}    # normalized name -> libtup

        self.symstore = e_symbols.SymStore()

        # we must be a voltron of each of these layers...
        self._arch_init()
        self._plat_init()

        self._mode_init("runforever",doc="run the trace until it exits")

    def _hook_fire(self, name, info, pend=False):
        # fire ( os possibly pend ) a hook
        if pend:
            print '*************PEND',name,info
            self.hookpends.append( (name,info) )
            return

        print '*************FIRE',name,info
        self.runagain = ( name in self.autocont )
        for hook in self.hooks.get(name,[]):
            try:
                hook(name,info)
            except Exception, e:
                print('hook error: %s %s' % (hook,e))

    def _hook_init(self, name, **hookdef):
        # creates a hook point
        self.hooks[name] = []
        self.hookdefs[name] = hookdef

    def _mode_init(self, name, **modeinfo):
        self.modes[name] = False
        self.modeinfo[name] = modeinfo

    def _fire_breakpoint(self, addr, info):

        # FIXME keep them together?
        self._clear_break((addr,info))

        for breakfunc in info.get('breakfuncs',[]):
            try:
                breakfunc(addr)
            except Exception, e:
                print('breakpoint function: %s %s' % (breakfunc,e))

        bptype = info.get('type')
        if bptype == 'fast':
            self.runagain = True
            return

        if bptype == 'stealth':
            return

        self._clear_breaks()
        self._hook_fire('breakpoint',{'addr':addr,'type':bptype})

    def _clear_breaks(self, breaks=None):
        # clear specified ( or all active ) breakpoints
        if breaks == None:
            # SPEEDHACK
            breaks = [ b for b in self.breaks.values() if b[1].get('active') ]

        self._plat_clear_breaks(breaks)

    def _write_breaks(self, breaks=None):
        # write specified ( or all enabled ) breakpoints
        if breaks != None:
            # SPEEDHACK
            breaks = [ b for b in self.breaks.values() if b[1]['enabled'] and not b[1]['active'] ]

        if breaks:
            self._plat_write_breaks(breaks)

    def _sync_cache(self):
        #self.flushCpuMem()
        self.flushCpuRegs()
        self.cache.clear()

    def checkPageWatchpoints(self):
        """
        Check if the given memory fault was part of a valid
        MapWatchpoint.
        """
        faultaddr,faultperm = self.platformGetMemFault()

        #FIXME this is some AWESOME but intel specific nonsense
        if faultaddr == None: return False
        faultpage = faultaddr & 0xfffff000

        wp = self.breakpoints.get(faultpage, None)
        if wp == None:
            return False

        self._fireBreakpoint(wp)

        return True

    def checkWatchpoints(self):
        # Check for hardware watchpoints
        waddr = self.archCheckWatchpoints()
        if waddr != None:
            wp = self.breakpoints.get(waddr, None)
            if wp:
                self._fireBreakpoint(wp)
                return True

    def _check_watchpoints(self):
        addr = self._arch_

    def _check_breakpoints(self):
        # check if we landed on a breakpoint
        #addr = self._plat_stoptobreak( self.getpc() )
        #info = self.breaks.get(addr)
        #if info == None:
            #return False
        bp = self._plat_curbreak()
        if bp == None:
            return False

        self._fire_breakpoint(addr,info)
        return True

    def getSymByAddr(self, addr):
        # FIXME DOCS
        return self.symstore.getSymByAddr(addr)

    def getSymByName(self, name):
        # FIXME DOCS
        return self.symstore.getSymByName(name)

    def _plat_bexhash(self, addr, size, norm, path):
        return None

    def _plat_bexsyms(self, addr, size, norm, path):
        return []

    def _lib_loadsyms(self, addr, size, norm, path):
        # check for local syms ( based on a "file hash" )
        bexhash = self._plat_bexhash(addr,size,norm,path)
        #if bexhash 
        return self._plat_bexsyms(addr,size,norm,path)

    def _lib_init(self, libva, libsize, libnorm, libpath, pend=False):
        # initialize library data structures and fire the hook
        libtup = (libva,libsize,libnorm,libpath)
        self.libsbyva[libva] = libtup
        self.libsbynorm[libnorm] = libtup

        def symloader():
            print 'SYM LOADER',libnorm
            return self._lib_loadsyms(libva,libsize,libnorm,libpath)

        symstore = e_symbols.SymStore(loader=symloader)
        self.symstore._add_sub_sym(libva, libsize, libnorm, symstore)

        self._hook_fire('libinit',{'va':libva,'size':libsize,'norm':libnorm,'path':libpath},pend=pend)

    def _lib_fini(self, libnorm):
        # fire the hook and tear down library structures
        libtup = self.libsbynorm.get(libnorm)
        if libtup == None:
            return

        libva,libsize,libnorm,libpath = libtup
        self._hook_fire('libfini',{'va':libva,'size':libsize,'norm':libnorm,'path':libpath})

        self.libsbyva.pop(libva,None)
        self.libsbynorm.pop(libnorm,None)
        self.symstore._del_sym(libnorm)

    def _get_cached(self, name, ctor):
        if not self.cache.has_key(name):
            self.cache[name] = ctor()
        return self.cache.get(name)

    def _lib_findmaps(self, magic, always=False):
        # A utility for platforms which lack library load
        # notification through the operating system
        mlen = len(magic)
        for addr,size,perms,path in self.getMemoryMaps():

            if not path:
                continue

            taste = self.readMemory(addr,mlen)
            if taste != magic:
                continue

            norm = self._plat_libnorm(path)
            if self.libsbynorm.get(norm):
                continue

            # FIXME get size from fmt somehow?
            self._lib_init(addr,size,norm,path,pend=True)

