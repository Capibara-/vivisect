"""
Vtrace Debugger Framework

Vtrace is a *mostly* native python debugging framework which
can be used to quickly write programatic debuggers and research
tools.

I'm not known for writting great docs...  but the code should
be pretty straight forward...

This has been in use for many years privately, but is nowhere
*near* free of bugs...  idiosyncracies abound.

==== Werd =====================================================

Blah blah blah... many more docs to come.

Brought to you by kenshoto.  e-mail invisigoth.

Greetz:
    h1kari - eeeeeooorrrmmm  CHKCHKCHKCHKCHKCHKCHK
    Ghetto - wizoo... to the tizoot.
    atlas - *whew* finally...  no more teasing...
    beatle/dnm - come out and play yo!
    The Kenshoto Gophers.
    Blackhats Everywhere.

"""
# Copyright (C) 2007 Invisigoth - See LICENSE file for details
import os
import re
import sys
import code
import copy
import time
import types
import struct
import getopt
import signal
import inspect
import platform
import traceback

import cPickle as pickle

import envi
import envi.cpu as e_cpu
import envi.bits as e_bits
import envi.memory as e_mem
import envi.registers as e_reg
import envi.expression as e_expr
import envi.symstore.resolver as e_resolv
import envi.symstore.symcache as e_symcache

import cobra
import vstruct
from vtrace.const import *

remote = None       # If set, we're a vtrace client (set to serverhost)
cobra_daemon = None
port = 0x5656
verbose = False

# File Descriptor / Handle Types
FD_UNKNOWN = 0 # Unknown or we don't have a type for it
FD_FILE = 1
FD_SOCKET = 2
FD_PIPE = 3
FD_LOCK = 4   # Win32 Mutant/Lock/Semaphore
FD_EVENT = 5  # Win32 Event/KeyedEvent
FD_THREAD = 6 # Win32 Thread
FD_REGKEY = 7 # Win32 Registry Key

# Vtrace Symbol Types
SYM_MISC = -1
SYM_GLOBAL = 0 # Global (mostly vars)
SYM_LOCAL = 1 # Locals
SYM_FUNCTION = 2 # Functions
SYM_SECTION = 3 # Binary section
SYM_META = 4 # Info that we enumerate

# Vtrace Symbol Offsets
VSYM_NAME = 0
VSYM_ADDR = 1
VSYM_SIZE = 2
VSYM_TYPE = 3
VSYM_FILE = 4

from vtrace.rmi import *
from vtrace.notifiers import *
from vtrace.breakpoints import *
from vtrace.watchpoints import *
import vtrace.util as v_util

class PlatformException(Exception):
    """
    A universal way to represent a failure in the
    platform layer for this tracer.  platformFoo methods
    should raise this rather than allowing their platform
    specific exception types (which don't likely pickle, or
    are not cross platform)
    """
    pass

class AccessViolation(Exception):
    """
    An exception which is raised on bad-touch to memory
    """
    def __init__(self, va, perm=0):
        self.va = va
        self.perm = perm
        Exception.__init__(self, "AccessViolation at 0x%.8x (%d)" % (va, perm))

class Trace(e_cpu.Cpu, e_resolv.SymbolResolver, object):
    """
    The main tracer object.  A trace instance is dynamically generated using
    this and *many* potential mixin classes.  However, API users should *not*
    worry about the methods that come from the mixins...
    """
    def __init__(self, wire=None):#, archname=None):

        self.pid = None
        self.sig = None

        #self.tid = None # this comes from e_cpu.Cpu

        self.wire = wire
        if self.wire == None:
            self.wire = self._plat_getwire()

        arch = self.wire.arch()

        self.plat = self.wire.plat()
        self.platver = self.wire.platver()

        e_cpu.Cpu.__init__(self, arch)
        self.sus_threads = {}   # A dictionary of suspended threads

        #e_resolv.SymbolResolver.__init__(self, width=self.archinfo.get('ptrsize'))
        #e_mem.IMemory.__init__(self, arch=self.arch)
        #e_reg.RegisterContext.__init__(self, self.arch)

        # Add event numbers to here for auto-continue
        #self.auto_continue = [NOTIFY_LOAD_LIBRARY, NOTIFY_CREATE_THREAD, NOTIFY_UNLOAD_LIBRARY, NOTIFY_EXIT_THREAD, NOTIFY_DEBUG_PRINT]

    def execute(self, cmdline):
        """
        Execute a new process from the given command.
        """
        self.pid = self._plat_exec(cmdline)
        self.metadata['cmdline'] = cmdline
        self._hook_fire('procinit',{'pid':self.pid,'cmdline':cmdline})

        # we may have an autocont on procinit...
        if self.wantrun():
            self.run()

    #def parseOpcodes(self, num, va=None):
        #'''
        #Returns next num of linear disasm'd opcodes objects.  Optionally pass
        #a va to start there instead of the current program counter.
        #'''
        #if num <= 0:
            #raise Exception('you must specify a positive number of opcodes')

        #if va == None:
            #va = self.getProgramCounter()

        #ops = []
        #for i in xrange(0, num):
            #op = self.parseOpcode(va)
            #ops.append(op)
            #va += op.size

        #return ops

    def getCurSignal(self):
        '''
        Retrieve the current signal/exception posted to the process.

        If there are no pending signals/exceptions the API will return
        None.  For POSIX systems, this will be a traditional POSIX signal.
        For Windows systems it will be a current exception code (if any).

        Example: sig = trace.getCurrentSignal()
        '''
        return self.sig

    def setCurSignal(self, sig=None):
        '''
        Set the currently pending signal for delivery to the target process on
        continue.  This is intended for use by programs wishing the mask or
        change the delivery of exceptions on a NOTIFY_SIGNAL event.

        Example:  trace.setCurrentSignal(None)
        '''
        self.sig = sig

    def addSigIgnore(self, sig):
        """
        Tell the tracer to ignore ( auto continue ) a signal.

        If the specified signal/exception code is caught, tracer
        execution continues as quickly as possible.  Used to "silence"
        C++ exceptions, SIGCHLD exits, etc...

        Example:
                t.addSigIgnore(sig)

        """
        self.signore.add(sig)

    def delSigIgnore(self, sig):
        """
        Remove a signal from the ignores list.

        Example:
            t.delSigIgnore(0xc010111c)
        """
        self.signore.remove(code)

    def attach(self, pid):
        """
        Attach to a new process ID.
        """
        self._plat_attach(pid)

        self.pid = pid
        self._hook_fire('procinit',{'pid':pid})

        # we may have an autocont on procinit...
        if self.wantrun():
            self.run()

    def stepi(self):
        """
        Execute the next single instruction.
        """
        self._sync_cache()
        self._plat_stepi()

    def wantrun(self):
        '''
        Check for conditions that would cause/prevent continued execution.
        '''
        if self.pid == None:
            return False

        if self.exitcode != None:
            return False

        if self.getMode("runforever"):
            return True

        if self.runagain:
            return True

        return False

    def run(self, addr=None):
        """
        Continue process execution until the next event.
        Optionally specify addr=<va> to run until a specific address.

        NOTE: this API will block.
        """
        if addr != None:

            def stoprunning(addr):
                self.delBreakByAddr(addr)
                self.modes['runforever'] = False

            self.modes['runforever'] = True
            self.addBreakByAddr(addr,breakfunc=stoprunning)

        self.runagain = True
        while self.wantrun():
            # check for pended hook events
            if self.hookpends:
                self._hook_fire( *self.hookpends.popleft() )
                continue

            self._sync_torun()
            self.running = True

            #self._hook_fire("continue",{'pid':self.pid,'sig':self.sig})

            self._plat_run()
            self.running = False

    def _sync_torun(self):
        self._check_delaybreaks()

        pc = self.getpc()
        bi = self.breaks.get(pc)

        # if we are at a break, step past it
        if bi != None and bi.get('enabled'):
            self.stepi()

        self._write_breaks()
        self._sync_cache()

    def kill(self):
        """
        Kill the target process for this trace (will result in process
        exit and fire appropriate notifiers)
        """
        return self._plat_pskill( self.pid )

    def detach(self):
        '''
        Detach from the currently attached process.
        '''
        self._sync_cache()

        tids = self.threads.keys()
        for tid in tids:
            self._hook_fire('threadfini',{'tid':tid})

        self._hook_fire('procfini',{'pid':self.pid})

        self._plat_detach()

        self.pid = None
        self.shutCpuCtx()

    #def release(self):
        #'''
        #Release resources for this tracer.  This API should be called
        #once you are done with the trace.
        #'''
        #if not self.released:
            #self.released = True
            #self.released = True
            #if self.attached:
                #self.detach()
            #self._cleanupResources()
            #self._plat_release()

    def getPid(self):
        """
        Return the pid for this Trace
        """
        return self.pid

    #def getNormalizedLibNames(self):
        #"""
        #Symbols are stored internally based off of
        #"normalized" library names.  This method returns
        #the list of normalized names for the loaded libraries.
#
        #(probably only useful for writting symbol browsers...)
        #"""
        #return self.getMeta("LibraryBases").keys()

    def getSymsForFile(self, libname):
        """
        Return the entire symbol list for the specified
        normalized library name.  The list is returned as
        "symtup" tuples of (va,size,name,type,fname).
        """
        self._loadBinaryNorm(libname)
        sym = self.getSymByName(libname)
        if sym == None:
            raise Exception('Invalid Library Name: %s' % libname)
        return sym.getSymList()

    def getSymByAddr(self, addr):
        """
        Return an envi symbol tuple (or None) for the given address.

        NOTE: (addr,size,name,type) (see SYM_* in envi/const.py for types)
        """
        return self.symcache.getSymByAddr(addr)

    def getSymByName(self, name):
        """
        Return an envi symbol tuple (or None) for the given name.

        NOTE: (addr,size,name,type) (see SYM_* in envi/const.py for types)
        """
        return self.symcache.getSymByName(addr)

    #def getSymByAddr(self, addr, exact=True):
        #"""
        #Return an envi Symbol object for an address.
        #Use exact=False to get the nearest previous match.
        #"""
        # NOTE: Override this from envi.SymbolResolver to do on-demand
        # file parsing.
#
        #r = e_resolv.SymbolResolver.getSymByAddr(self, addr, exact=exact)
        #if r != None:
            #return r

        # See if we need to parse the file.
        #mmap = self.getMemoryMap(addr)
        #if mmap == None:
            #return None

        #va, size, perms, fname = mmap

        #if not self._loadBinary(fname):
            #return None

        # Take a second shot after parsing
        #return e_resolv.SymbolResolver.getSymByAddr(self, addr, exact=exact)

    #def getSymByAddrThunkAware(self, va):
        #'''
        #TODO: DO NOT USE THIS FUNCTION, GOING AWAY.
        #getBestSymEtc? depth / aggressiveness?

        #for the given va:
        #1. attempt to get the sym by using getSymByAddr
        #2. if 1 fails, check the target of the branch for a sym.

        #returns a tuple (sym, is_thunk).  sym is None if no sym is found.
        #'''
        #sym = self.getSymByAddr(va)
        #if sym != None:
            #return str(sym), False

        #try:
            #op = self.parseOpcode(va)
            #for tva, tflags in op.getTargets(emu=self):
                #if tva == None:
                    #continue

                #sym = self.getSymByAddr(tva)
                #if sym != None:
                    #return str(sym), True

        #except Exception as e:
            ## getTargets->readMemory error on bva
            #print('getSymByAddrThunkAware: %s' % repr(e))

        #return None, False

    #def getSymByName(self, name):
        #"""
        #Return an envi.Symbol object for the given name (or None)
        #"""
        #self._loadBinaryNorm(name)
        #return e_resolv.SymbolResolver.getSymByName(self, name)

    def setSymCachePath(self, path):
        '''
        Set the symbol cache path for the tracer.

        The "path" syntax is a ; seperated list of either directories
        or cobra URIs which implement the SymbolCache interface.

        Example:
            trace.setSymCachePath('/home/invisigoth/.envi/symcache;cobra://symbols.com/SymbolCache')

        NOTE: vdb automatically handles this with a config option
        '''
        self.symcache = e_symcache.SymbolCachePath(path)

    #def searchSymbols(self, regex, libname=None):
        #'''
        #Search for symbols which match the given regular expression.  Specify
        #libname as the "normalized" library name to only search the specified
        #lib.

        #Example:  for sym in trace.searchSymbols('.*CreateFile.*', 'kernel32'):
        #'''
        #reobj = re.compile(regex)
        #if libname != None:
            #libs = [libname, ]
        #else:
            #libs = self.getNormalizedLibNames()

        #ret = []
        #for lname in libs:
            #for sym in self.getSymsForFile(lname):
                #symstr = str(sym)
                #if reobj.match(symstr):
                    #ret.append(sym)
        #return ret

    #def getRegisterContext(self, tid=None):
        #"""
        #Retrieve the envi RegisterContext object for the specified thread.
        #Use this API to iterate over threads register values without setting
        #the global tracer thread context.
        #"""
        #print 'HI' * 100
        #if tid == None:
            #tid = self.tid

        #regcache = self._get_cached('regs',dict)
        #regcache = self.cache.get('regs')
        #if regcache == None:
            #regcache = {}
            #self.cache['regs'] = regcache

        #regctx = regcache.get(tid)
        #if regctx == None:
            #regctx = self._plat_getregctx(tid)
            #regctx.setIsDirty(False)
            #regcache[tid] = regctx

        #return regctx

#######################################################################
#
# We mirror the RegisterContext API using our own thread index based
# cache.  These APIs must stay in sync with envi.registers.RegisterContext
# NOTE: for now we only need to over-ride get/setRegister because all the
# higher level APIs call them.
#

    #def getRegister(self, idx):
        #ctx = self.getRegisterContext()
        #return ctx.getRegister(idx)

    #def setRegister(self, idx, value):
        #ctx = self.getRegisterContext()
        #ctx.setRegister(idx, value)

#######################################################################

    def allocateMemory(self, size, perms=e_mem.MM_RWX, addr=None):
        """
        Allocate a chunk of memory inside the target process.

        Memory wil be mapped rwx unless otherwise specified with
        perms=envi.memory.MM_FOO values. Optionally you may *suggest* an
        address to the allocator, but there is no guarentee.  Returns the
        mapped memory address.
        """
        addr = self._plat_memalloc(size, perms=perms, addr=addr)
        self.cache.pop('memmaps',None)
        return addr

    def protectMemory(self, addr, size, perms):
        """
        Change the page protections on the specified region of memory.

        See envi.memory for perms values.
        """
        self._plat_memprotect(addr, size, perms)
        self.cache.pop('memmaps',None)

    def readMemory(self, address, size):
        """
        Read process memory from the specified address.
        """
        return self._plat_memread(long(address), long(size))

    def writeMemory(self, addr, bytez):
        """
        Write the given bytes to the address in the current process.
        """
        self._plat_memwrite(long(address), bytez)

    def searchMemory(self, needle, regex=False):
        """
        Search all of process memory for a sequence of bytes.
        """
        ret = e_mem.IMemory.searchMemory(self, needle, regex=regex)
        self.setMeta('search', ret)
        self.setVariable('search', ret)
        return ret

    def searchMemoryRange(self, needle, address, size, regex=False):
        """
        Search a memory range for the specified sequence of bytes
        """
        ret = e_mem.IMemory.searchMemoryRange(self, needle, address, size, regex=regex)
        self.setMeta('search', ret)
        self.setVariable('search', ret)
        return ret

    def setMeta(self, name, value):
        """
        Set some metadata.  Metadata is a clean way for
        arbitrary trace consumers (and notifiers) to present
        and track additional information in trace objects.

        Any modules which use this *should* initialize them
        on attach (so when they get re-used they're clean)

        Some examples of metadata used:
        ShouldBreak - We're expecting a non-signal related break
        ExitCode - The int() exit code  (if exited)
        PendingSignal - The current signal

        """
        self.metadata[name] = value

    def getMeta(self, name, default=None):
        """
        Get some metadata.  Metadata is a clean way for
        arbitrary trace consumers (and notifiers) to present
        and track additional information in trace objects.

        If you specify a default and the key doesn't exist, not
        not only will the default be returned, but the key will
        be set to the default specified.
        """
        return self.metadata.get(name,default)

    def getMode(self, name):
        """
        Determine if the given mode is enabled.

        Example:
            if t.getMode('foomode'):
                print('the trace is in foo mode!')
        """
        return self.modes.get(name,False)

    def setMode(self, name, value=True):
        """
        Enable/disable various modes within the tracer.

        all:
            runforever      - on run() continue running to exit

        linux:
            syscall         - break on syscall entry/exits

        """
        if not self.modes.has_key(name):
            raise Exception("Mode %s not supported on this platform" % name)
        self.modes[name] = bool(value)

    def injectso(self, filename):
        """
        Inject a shared object into the target of the trace.  So, on windows
        this is easy with InjectDll and on *nix... it's.. fugly...

        NOTE: This method will likely cause the trace to run.  Do not call from
              within a notifier!
        """
        self._plat_injectso(filename)
        self.cache.pop('memmaps',None)

    def ps(self):
        """
        Return a list of proccesses which are currently running on the
        system.
        (pid, name)
        """
        return self._plat_pslist()

    def addBreakByExpr(self, expr, mode=None, breakfunc=None):
        '''
        Add a breakpoint by expression.  If the expression is *not* resolved
        immediately, the it is added to a list of "delayed" breaks which
        will be added once the expression resolves to an address.

        Example:
            trace.addBreakByExpr('kernel32.CreateFileA + ecx')
        '''
        addr = self.parseExpression(expr)
        if addr != None:
            self.addBreakByAddr(addr,mode=mode,breakfunc=breakfunc)
            return

        self.delaybreaks.append( (expr,mode,breakfunc) )

    def _check_delaybreaks(self):
        delays = self.delaybreaks

        self.delaybreaks = []
        for delay in delays:
            expr,mode,breakfunc = delay
            try:
                addr = self.parseExpression(expr)
                self.addBreakByAddr(addr,mode=mode,breakfunc=breakfunc)
            except Exception, e:
                self.delaybreaks.append( delay )

    def addBreakByAddr(self, addr, mode=None, breakfunc=None):
        '''
        Add a breakpoint by address.

        Optional breakfunc:
            breakfunc(addr) will be called back on breakpoint hit

        Optional mode:
            * fast      - tightest loop, minimal callbacks, no other break cleanup
            * stealth   - *only* triggers breakfunc callbacks (used to emulate other hooks)

        Example:
            def breakhit(addr):
                print('hit my break!')

            trace.addBreakByAddr(0x7c770308, breakfunc=breakhit)
        '''
        bp = self.breaks.get(addr)
        if bp == None:
            info = {'mode':mode,'breakfuncs':[],'active':False,'enabled':True}
            bp = (addr,info)
            self.breaks[addr] = bp

        if breakfunc != None:
            bp[1]['breakfuncs'].append(breakfunc)

    def delBreakByAddr(self, addr):
        '''
        Remove a breakpoint by address.
        '''
        self.breaks.pop(addr,None)

    #def setBreakEnabled(self, addr, status):
        #'''
        #Enable/Disable breakpoints.
        #Example:
            #t.setBreakEnabled(0x41414100,False)
        #'''
        #bp = self.breaks.get(addr)
        #if bp == None:
            #raise Exception('invalid break addr: 0x%.8x' % addr)
        #bp[1]['enabled'] = status

    #def isBreakEnabled(self, addr):
        #bp = self.breaks.get(addr)
        #if bp == None:
            #raise Exception('invalid break addr: 0x%.8x' % addr)
        #return bp[1]['enabled']

    def call(self, address, args, convention=None):
        """
        Setup the "stack" and call the target address with the following
        arguments.  If the argument is a string or a buffer, copy that into
        memory and hand in the argument.

        The current state of ALL registers are returned as a dictionary at the
        end of the call...

        Additionally, a "convention" string may be specified that the underlying
        platform may be able to interpret...
        """
        return self.platformCall(address, args, convention)

    def getFds(self):
        """
        Get a list of (fd, type, repr) tuples for open descriptors.
        """
        return self._get_cached('fds',self._plat_getfds())

    def getMemoryMaps(self):
        """
        Retrieve the list of memory maps for the process.

        Example:
            for addr,size,perms,file in t.getMemoryMaps():
                print('%.8x - %s' % (addr,file))
        """
        return self._get_cached('mmaps', self._plat_memmaps)

    #def getMemoryFault(self):
        #'''
        #If the most receent event is a memory access error, this API will
        #return a tuple of (<addr>, <perm>) on supported platforms.  Otherwise,
        #a (None, None) will result.

        #Example:
        #import envi.memory as e_mem
        #vaddr, vperm = trace.getMemoryFault()
        #if vaddr != None:
            #print 'Memory Fault At: 0x%.8x (perm: %d)' % (vaddr, vperm)
        #'''
        #return self.platformGetMemFault()

    #def enableAutoContinue(self, event):
        #"""
        #Put the tracer object in to AutoContinue mode
        #for the specified event.  To make all events
        #continue running see RunForever mode in setMode().
        #"""
        #if event not in self.auto_continue:
            #self.auto_continue.append(event)

    def addAutoCont(self, evtname):
        '''
        Enable auto-continue behavior for the specified event name.

        Example:

            t.addAutoCont('libinit')
            # we now continue running on library loads
        '''
        self.autocont.add(hookname)

    def delAutoCont(self, evtname):
        '''
        Disable auto-continue behavior for the specified event name.

        Example:

            t.delAutoCont('threadinit')
            # we now stop on thread creations
        '''
        self.autocont.remove(hookname)

    def getAutoCont(self):
        '''
        Get a list of the current auto-continue events.
        '''
        return list(self.autocont)

    #def disableAutoContinue(self, event):
        #"""
        #Disable Auto Continue for the specified
        #event.
        #"""
        #if event in self.auto_continue:
            #self.auto_continue.remove(event)

    #def getAutoContinueList(self):
        #"""
        #Retrieve the list of vtrace notification events
        #that will be auto-continued.
        #"""
        #return list(self.auto_continue)

    def parseExpression(self, expression):
        """
        Parse a python expression with many useful helpers mapped
        into the execution namespace.

        Example: trace.parseExpression("ispoi(ecx+ntdll.RtlAllocateHeap)")
        """
        locs = VtraceExpressionLocals(self)
        return long(e_expr.evaluate(expression, locs))

    def sendBreak(self, wait=None):
        """
        Send an asynchronous break signal to the target process.

        If wait is specified, block until either <wait> seconds
        or the process has stopped.
        """
        self.modes['runforever'] = False

        if wait == None:
            return self._plat_sendbreak()

        evt = threading.Event()
        def waitbreak(evtname,evtinfo):
            evt.set()
            self.delTraceHook('break',waitbreak)

        self.addTraceHook('break',waitbreak)

        self._plat_sendbreak()
        return evt.wait(timeout=wait)

    def getStackTrace(self, tid=None):
        """
        Returns a list of (instruction pointer, stack frame) tuples.

        If stack tracing results in an error, the error entry will
        be (-1, -1).
        """
        return self._plat_stacktrace(tid=tid)

    def getThreads(self):
        """
        Get a dictionary of <threadid>:<tinfo> pairs where
        tinfo is platform dependant, but is typically either
        the top of the stack for that thread, or the TEB on
        win32
        """
        threads = self.cache.get('threads')
        if threads == None:
            threads = self._plat_getthreads()
            self.cache['threads'] = threads
        return threads

    #def getCurrentThread(self):
        #'''
        #Return the thread id of the currently selected thread.
        #'''
        #return self.tid

    # depricated for setCpuCtx()
    #def selectThread(self, tid):
        #"""
        #Set the "current thread" context to the given thread id.
        #(For example stack traces and register values will depend
        #on the current thread context).  By default the thread
        #responsible for an "interesting event" is selected.
        #"""
        #if self.threads.get(tid) == None:
            #raise Exception('invalid thread id: %s' % tid)
        #self.tid = tid

    def isThreadSuspended(self, threadid):
        """
        Used to determine if a thread is suspended.
        """
        return self.sus_threads.get(threadid, False)

    def suspend(self, tid):
        """
        Suspend a thread.
        ( thread no longer executes on process continue )

        Example:
            t.suspendThread( tid )
        """
        if self.sus_threads.get(threadid):
            raise Exception("The specified thread is already suspended")
        if self.threads.get(tid) == None:
            raise Exception("invalid thread id: %s" % tid)
        self._plat_susthread(tid)
        self.sus_threads[tid] = True

    def resumeThread(self, tid):
        """
        Resume a suspended thread.
        """
        if not self.sus_threads.get(tid):
            raise Exception('thread is not suspended: %s' % tid)
        self._plat_resthread(tid)
        self.sus_threads.pop(tid)

    def injectThread(self, pc):
        """
        Inject a thread executing at the specified address.

        Example:
            t.injectThread( shellcode )
        """
        self._plat_injthread(pc)

    def joinThread(self, tid, timeout=None):
        '''
        Run the trace in a loop until the specified thread exits.
        '''
        scope = {}
        evt = threading.Event()
        def hookexit(evtname,evtinfo):
            if evtinfo.get('tid') == tid:
                evt.set()
            scope['exit'] = evtinfo.get('exit')
            self.delTraceHook('threadexit',hookexit)

        self.addTraceHook('threadexit',hookexit)
        evt.wait(timeout=timeout)
        return scope.get('exit')

    def getStructNames(self, namespace=None):
        '''
        This method returns either the structure names, or
        the structure namespaces that the target tracer is aware
        of.  If "namespace" is specified, it is structures within
        that namespace, otherwise it is "known namespaces"

        Example: namespaces = trace.getStructNames()
                 ntdll_structs = trace.getStructNames(namespace='ntdll')
        '''
        if namespace:
            return self.vsbuilder.getVStructNames(namespace=namespace)
        return self.vsbuilder.getVStructNamespaceNames()

    def getStruct(self, sname, va=None):
        """
        Retrieve a vstruct structure optionally populated with memory from
        the specified address.  Returns a standard vstruct object.
        """
        # Check if we need to parse symbols for a library
        libbase = sname.split('.')[0]
        self._loadBinaryNorm(libbase)

        if self.vsbuilder.hasVStructNamespace(libbase):
            vs = self.vsbuilder.buildVStruct(sname)

        # FIXME this is deprecated and should die...
        else:
            vs = vstruct.getStructure(sname)

        if vs == None:
            return None

        if va == None:
            return vs

        bytez = self.readMemory(va, len(vs))
        vs.vsParse(bytez)
        return vs

    def setVariable(self, name, value):
        """
        Set a named variable in the trace which may be used in
        subsequent VtraceExpressions.

        Example:
        trace.setVariable("whereiam", trace.getProgramCounter())
        """
        self.localvars[name] = value

    def getVariable(self, name):
        """
        Get the value of a previously set variable name.
        (or None on not found)
        """
        return self.localvars.get(name)

    def getVariables(self):
        """
        Get the dictionary of named variables.
        """
        return dict(self.localvars)

    #def hex(self, value):
        #"""
        #Much like the python hex routine, except this will automatically
        #pad the value's string length out to pointer width.
        #"""
        #width = self.arch.getPointerSize()
        #return e_bits.hex(value, width)

    #def buildNewTrace(self):
        #'''
        #Build a new/clean trace "like" this one.  For platforms where a
        #special trace was handed in, this allows initialization of a new one.
        #For most implementations, this is very simple....

        #Example:
            #if need_another_trace:
                #newt = trace.buildNewTrace()
        #'''
        #return self.__class__()

class VtraceExpressionLocals(e_expr.MemoryExpressionLocals):
    """
    A class which serves as the namespace dictionary during the
    evaluation of an expression on a tracer.
    """
    def __init__(self, trace):
        e_expr.MemoryExpressionLocals.__init__(self, trace, symobj=trace)
        self.trace = trace
        self.update({
                'trace':trace,
                'vtrace':vtrace
        })
        self.update({
            'frame':self.frame,
            'teb':self.teb,
            'bp':self.bp,
            'meta':self.meta,
            'go':self.go,
        })

    def __getitem__(self, name):

        valu = self.trace.getreg(name)
        if valu != None:
            return valu

        # Check local variables
        locs = self.trace.getVariables()
        r = locs.get(name, None)
        if r != None:
            return r

        return e_expr.MemoryExpressionLocals.__getitem__(self, name)

    def go(self):
        '''
        A shortcut for trace.runAgain() which may be used in
        breakpoint code (or similar even processors) to begin
        execution again after event processing...
        '''
        self.trace.runagain = True

    def frame(self, index):
        """
        Return the address of the saved base pointer for
        the specified frame.

        Usage: frame(<index>)
        """
        stack = self.trace.getStackTrace()
        return stack[index][1]

    def teb(self, threadnum=None):
        """
        The expression teb(threadid) will return whatever the
        platform stores as the int for threadid.  In the case
        of windows, this is the TEB, others may be the thread
        stack base or whatever.  If threadid is left out, it
        uses the threadid of the current thread context.
        """
        if threadnum == None:
            # Get the thread ID of the current Thread Context
            threadnum = self.trace.getMeta("ThreadId")

        teb = self.trace.getThreads().get(threadnum, None)
        if teb == None:
            raise Exception("ERROR - Unknown Thread Id %d" % threadnum)

        return teb

    def bp(self, bpid):
        """
        The expression bp(0) returns the resolved address of the given
        breakpoint
        """
        bp = self.trace.getBreakpoint(bpid)
        if bp == None:
            raise Exception("Unknown Breakpoint ID: %d" % bpid)
        return bp.resolveAddress(self.trace)

    def meta(self, name):
        """
        An expression friendly (terse) way to get trace metadata
        (equiv to trace.getMeta(name))

        Example: meta("foo")
        """
        return self.trace.getMeta(name)

def reqTargOpt(opts, targ, opt, valstr='<value>'):
    val = opts.get( opt )
    if val == None:
        raise Exception('Target "%s" requires option: %s=%s' % (targ, opt, valstr))
    return val

# FIXME PY3
from urlparse import urlparse

import vtrace.platforms.linux as vt_plat_linux

platarch = {
    ('linux','amd64'):vt_plat_linux.LinuxAmd64Trace,
}

def getTrace(target=None):
    """
    Return a tracer object appropriate for this platform.
    This is the function you will use to get a tracer object
    with the appropriate ancestry for your host.

    ex. mytrace = vtrace.getTrace()


    NOTE: Use the release() method on the tracer once debugging
          is complete.  This releases the tracer thread and allows
          garbage collection to function correctly.

    wire://<host>:<port>/

    gdb://<host>:<port>/?plat=<plat>&arch=<arch>

    vmware://<host>:<port>/?plat=<plat>&arch=<arch>
        ( most often vmware://localhost:8832/ )

    """
    wire = None
    arch = envi.getCurrentArch()
    plat = envi.getCurrentPlat()

    if target != None:
        url = urlparse(target)

        if url.scheme == 'wire':
            wire = WireProto(target)
            arch = wire.arch()
            plat = wire.plat()

        #if url.scheme == 'gdb':
        #if url.scheme == 'vmware':


    #if target:
    #if target == 'gdbserver':
        #host = reqTargOpt(kwargs, 'gdbserver', 'host', '<host>')
        #port = reqTargOpt(kwargs, 'gdbserver', 'port', '<port>')
        #arch = reqTargOpt(kwargs, 'gdbserver', 'arch', '<i386|amd64|arm>')
        #plat = reqTargOpt(kwargs, 'gdbserver', 'plat', '<windows|linux>')
        #if arch not in ('i386', 'amd64', 'arm'):
            #raise Exception('Invalid arch specified for "gdbserver" target: %s' % arch)
        #if plat not in ('windows', 'linux'):
            #raise Exception('Invalid plat specified for "gdbserver" target: %s' % plat)

    #if target == 'vmware32':
        #import vtrace.platforms.vmware as vt_vmware
        #host = reqTargOpt(kwargs, 'vmware32', 'host', '<host>')
        #port = int( reqTargOpt(kwargs, 'vmware32', 'port', '<port>') )
        #plat = 'windows'
        #plat = reqTargOpt(kwargs, 'vmware32', 'plat', '<windows|linux>')
        #if plat not in ('windows', 'linux'):
            #raise Exception('Invalid plat specified for "vmware32" target: %s' % plat)

        #return vt_vmware.VMWare32WindowsTrace( host=host, port=port )


    cls = platarch.get( (plat,arch) )
    if cls == None:
        raise Exception('no trace for plat: %s arch: %s' % (plat,arch))

    return cls(wire=wire)

    #if plat == "windows":
        #if arch == "i386":
            #return v_win32.Windowsi386Trace()

        #if arch == "amd64":
            #return v_win32.WindowsAmd64Trace()

    #if plat == "linux":

        #if arch == "i386":
            #return vt_plat_linux.Linuxi386Trace(wire=wire)

        #if arch == "amd64":
            #return vt_plat_linux.LinuxAmd64Trace(wire=wire)

        #if arch in ("armv6l","armv7l"):
            #return vt_plat_linux.LinuxArmTrace(wire=wire)

    #if plat == 'freebsd':

        #if arch == "i386":
            #return v_freebsd.FreeBSDi386Trace(wire=wire)

        #if arch == "amd64":
            #return v_freebsd.FreeBSDAmd64Trace(wire=wire)

    #if plat == 'darwin':

        #if arch == 'i386':
            #return v_darwin.Darwini386Trace()

        ##if arch == 'amd64':
            #return v_darwin.DarwinAmd64Trace()

    #raise Exception('FIXME need tracer for %s - %s' % (plat,arch))

#def getEmu(trace, arch=None):
    #'''
    #See comment for emulator from trace (in envitools); does not set any
    #registers or mem.

    #TODO: this really belongs in envitools, or somewhere else, but putting it
    #in envitools causes a circular import problem due to the TraceEmulator.
    #'''
    #if arch == envi.ARCH_DEFAULT:
        #arch_name = trace.getMeta('Architecture')
    #else:
        #arch_name = envi.getArchById(trace.arch)

    #arch_mod = envi.getArchModule(arch_name)
    #emu = arch_mod.getEmulator()
    #return emu
