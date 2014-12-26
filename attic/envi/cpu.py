import itertools

import envi.memory as e_mem
import envi.registers as e_regs

class TerseApi:

    def getpc(self,tid=None):
        return self.getCpuRegs(tid=tid).getpc()

    def getsp(self,tid=None):
        return self.getCpuRegs(tid=tid).getsp()

    def getregs(self,tid=None):
        return self.getCpuRegs(tid=tid)

    def getreg(self,reg,tid=None):
        return self.getCpuRegs(tid=tid).get(reg)

    def setreg(self,reg,val,tid=None):
        return self.getCpuRegs(tid=tid).set(reg,val)

    def getmem(self, va, size):
        return self.readMemory(va,size)

    def setmem(self, va, bytez):
        return self.writeMemory(va,size)

    #def __getitem__(self, key):
    #def __setitem__(self, key, val):

    def __getslice__(self, va, size):
        return self.readMemory(va,size)

class Cpu(e_mem.IMemory,TerseApi):
    '''
    The Cpu class implements the synthesis of the various envi APIs.

    At it's core, the Cpu is the base class from which others such
    as tracers / emulators should extend.  It abstracts the idea of
    threads to manage multiple register contexts as well as memory.

    The Cpu class can additionally track the idea of "dirty" cache
    elements to facilitate forward caching.
    '''
    def __init__(self, arch):
        e_mem.IMemory.__init__(self, arch)

        self.tid = None
        self.tidgen = itertools.count(0)

        self.threads = {}
        self.thrregs = {}
        self.thrload = {}

    def initCpuCtx(self, tid=None):
        '''
        Initialize an execution context, optionally specifying a
        "thread id" to use in tracking this context.

        Returns:
            The id of the new execution context.

        Example:
            tid = cpu.initCpuCtx()
        '''
        if tid == None:
            tid = self.tidgen.next()


        # lets be helpful about re-init ( trace attach/threads )
        if self.threads.get(tid):
            self.setCpuCtx(tid)
            return tid

        regs = e_regs.RegisterContext( self.arch )

        self.threads[tid] = True
        self.thrregs[tid] = regs

        self.setCpuCtx(tid)

        return tid

    def finiCpuCtx(self, tid, setid=None):
        '''
        Tells the Cpu to tear down the given excution context.
        '''
        if self.tid == tid:
            self.tid = None

        self.threads.pop(tid,None)
        self.thrregs.pop(tid,None)

        if setid != None:
            self.tid = setid

    def shutCpuCtx(self):
        '''
        Shutdown all the trash compactors on the detention level!

        This method will call finiCpuCtx on all the context id's being
        tracked by this Cpu and return a list of the closed ids.
        '''
        tids = self.threads.keys()
        [ self.finiCpuCtx(tid) for tid in tids ]
        return tids

    def setCpuCtx(self, tid):
        '''
        Select an execution context (read. thread) by id.

        This updates the current "default context" to the specified
        thread by id.  Future calls to things like getregs() will default
        to the specified context.
        '''
        if self.threads.get(tid) == None:
            raise Exception('Invalid Cpu Context: %d' % tid)
        self.tid = tid

    def getCpuRegs(self, tid=None):
        '''
        Retrieve an envi RegisterContext from the Cpu.
        Optionally specify tid to retrieve the RegisterContext
        from a specific execution context ( read. thread ).

        Returns:
            envi RegisterContext or None

        Example:

        '''
        if tid == None:
            tid = self.tid
        regs = self.thrregs.get(tid)

        if not self.thrload.get(tid):
            self.thrload[tid] = True
            regs.load( self._loadCpuRegs(tid) )

        return regs

    def flushCpuRegs(self):
        '''
        Trigger the _saveCpuRegs callback for any dirty reg contexts.
        Additionally, annotate that the reg ctx should be loaded on
        access using the _loadCpuRegs callback...
        '''
        flushes = []
        for tid,regs in self.thrregs.items():
            self.thrload.pop(tid,None)
            if regs.dirty():
                regdict = regs.save()
                flushes.append( (tid,regdict) )
        if flushes:
            self._saveCpuRegs(flushes)

    def _loadCpuRegs(self, tid):
        '''
        Allows inheriters to overload how regs get initialized.
        '''
        return {}

    def _saveCpuRegs(self, reglist):
        '''
        Allows inheriters to overload how regs get saved/flushed.
        It is called with a list of (tid,regdict) tuples for each
        dirty register context.
        '''
        pass


    #def flushmem(self):
        #pass

    #def flushregs(self):
        #pass

    # sub-classes may over-ride the following methods to use
    # the caching behavior.
    #def _flush_savemem(self, va, bytez):
        #pass
    ##def _flush_saveregs(self, tid, regs):
        #pass
