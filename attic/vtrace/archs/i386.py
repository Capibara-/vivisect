"""
x86 Support Module
"""
# Copyright (C) 2007 Invisigoth - See LICENSE file for details
import vtrace
import struct
import traceback
import types
import vtrace.breakpoints as breakpoints

import envi.archs.i386 as e_i386
import vtrace.archs.base as vt_arch_base

# Pre-populating these saves a little processing
# time (important in tight watchpoint loops)
drnames = ["debug%d" % d for d in range(8)]

dbg_status = "debug6"
dbg_ctrl = "debug7"

dbg_execute    = 0
dbg_write      = 1
dbg_read_write = 3

dbg_types = {
    "x":dbg_execute,
    "w":dbg_write,
    "rw":dbg_read_write,
}

class i386Trace(vt_arch_base.TraceArch):

    def _plat_curbreak(self):
        return self.breaks.get( self.getpc() - 1 )

    #archsize = 4
    #archname = 'i386'

    #def _arch_init(self):
        #self.archname = 'i386'
        #self.setMeta('architecture','i386')

    #def _arch_init(self):
        #self._arch_dbgregs = [0, 0, 0, 0]

    #def _arch_bpinit(self, addr, info):
        #self.setmem(addr,info['saved'])
        
    #def _arch_bpfini(self, addr, info):
        #info['saved'] = self.getmem(addr,1)
        #self.setmem(addr,'\xcc')

    def _arch_checkwatchs(self):
        dbg6 = self.getreg('debug6')

    #def archCheckWatchpoints(self):
        #regs = self.getRegisters()
        #status = regs.get(dbg_status)
        #print "STATUS %.8x" % status
        #if status == None:
            #return None
        #x = status & 0x0f
        #if not x:
            #return None

        #for i in range(4):
            #if (x >> i) & 1:
                #return self._arch_dbgregs[i]
        #return None

    def _arch_watchinit(self, addr, size=4, perms="rw"):

        try:
            idx = self._arch_dbgregs.index(0)
        except ValueError, e:
            raise Exception("ERROR: there...  are... 4... debug registers!")

        #idx = None
        #for i in range(4):
            #if not self._arch_dbgregs[i]:
                #idx = i
                #break

        #if idx == None:
            #raise Exception("ERROR: there...  are... 4... debug registers!")

        pbits = dbg_types.get(perms)
        if pbits == None:
            raise Exception("Unsupported watchpoint perms %s (x86 supports x,w,rw)" % perms)

        if pbits == dbg_execute and size != 1:
            raise Exception("Watchpoint for execute *must* be 1 byte long!")

        if size not in [1,2,4]:
            raise Exception("Unsupported watchpoint size %d (x86 supports 1,2,4)" % size)

        ctrl = 0

        self._arch_dbgregs[idx] = addr

        ctrl |= 1 << (2*idx)           # Enabled
        mask = ((size-1) << 2) + pbits # perms and size
        ctrl |= (mask << (16+(4*idx)))

        for tid in self.getThreads().keys():
            ctx = self.getRegisterContext(tid)
            debug7 = ctx.getRegister(e_i386.REG_DEBUG7)
            #print "debug%d: %.8x debug7: %.8x" % (idx,addr,ctrl|debug7)
            ctx.setRegister(e_i386.REG_DEBUG7, debug7 | ctrl)
            ctx.setRegister(e_i386.REG_DEBUG0 + idx, addr)
        return

    def _arch_watchfini(self, addr):

        # FIXME WHAT ABOUT NEW THREADS!

        try:
            idx = self._arch_dbgregs.index(addr)
        except ValueError, e:
            raise Exception("Watchpoint not found at 0x%.8x" % addr)

        self._arch_dbgregs[idx] = 0

        ctrl_disable = ~(1 << (2*idx))      # we are not enabled
        ctrl_disperm = ~(0xf << (16+(4*idx))) # mask off the rwx stuff
        ctrl_mask = ctrl_disable & ctrl_disperm

        for tid in self.getThreads().keys():
            ctx = self.getRegisterContext(tid)
            ctrl = ctx.getRegister(e_i386.REG_DEBUG7)
            ctrl &= ctrl_mask
            #print "debug%d: %.8x debug7: %.8x" % (idx,address,ctrl|ctrl_orig)
            ctx.setRegister(e_i386.REG_DEBUG7, ctrl)
            ctx.setRegister(e_i386.REG_DEBUG0 + idx, 0)
        return

    def _arch_stacktrace(self, tid):
        current = 0
        sanity = 1000
        frames = []

        eip = self.getpc()
        ebp = self.getreg('ebp')

        frames.append((eip,ebp))

        done = set()
        while ebp != 0 and current < sanity:
            try:

                frame = self.readMemoryFmt(ebp,'<II')
                if frame in done:
                    break

                ebp = frame[0]
                frames.append(frame)

            except:
                break

        return frames


class i386WatchMixin:
    def __init__(self):
        # Which ones are in use / enabled.
        self.hwdebug = [0, 0, 0, 0]
        # FIXME change this to storing debug0 index and using setRegister()

    def archAddWatchpoint(self, address, size=4, perms="rw"):

        idx = None
        for i in range(4):
            if not self.hwdebug[i]:
                idx = i
                break

        if idx == None:
            raise Exception("ERROR: there...  are... 4... debug registers!")

        pbits = dbg_types.get(perms)
        if pbits == None:
            raise Exception("Unsupported watchpoint perms %s (x86 supports x,w,rw)" % perms)

        if pbits == dbg_execute and size != 1:
            raise Exception("Watchpoint for execute *must* be 1 byte long!")

        if size not in [1,2,4]:
            raise Exception("Unsupported watchpoint size %d (x86 supports 1,2,4)" % size)

        ctrl = 0

        self.hwdebug[idx] = address

        ctrl |= 1 << (2*idx)           # Enabled
        mask = ((size-1) << 2) + pbits # perms and size
        ctrl |= (mask << (16+(4*idx)))
        #ctrl |= 0x100 # Local exact (ignored by p6+ for read)

        for tid in self.getThreads().keys():
            ctx = self.getRegisterContext(tid)
            ctrl_orig = ctx.getRegister(e_i386.REG_DEBUG7)
            #print "debug%d: %.8x debug7: %.8x" % (idx,address,ctrl|ctrl_orig)
            ctx.setRegister(e_i386.REG_DEBUG7, ctrl_orig | ctrl)
            ctx.setRegister(e_i386.REG_DEBUG0 + idx, address)
        return

    def archRemWatchpoint(self, address):
        idx = None
        for i in range(4):
            if self.hwdebug[i] == address:
                idx = i
                break

        if idx == None:
            raise Exception("Watchpoint not found at 0x%.8x" % address)

        self.hwdebug[idx] = 0

        ctrl_disable = ~(1 << (2*idx))      # we are not enabled
        ctrl_disperm = ~(0xf << (16+(4*idx))) # mask off the rwx stuff
        ctrl_mask = ctrl_disable & ctrl_disperm

        for tid in self.getThreads().keys():
            ctx = self.getRegisterContext(tid)
            ctrl = ctx.getRegister(e_i386.REG_DEBUG7)
            ctrl &= ctrl_mask
            #print "debug%d: %.8x debug7: %.8x" % (idx,address,ctrl|ctrl_orig)
            ctx.setRegister(e_i386.REG_DEBUG7, ctrl)
            ctx.setRegister(e_i386.REG_DEBUG0 + idx, 0)
        return

    def archCheckWatchpoints(self):
        regs = self.getRegisters()
        status = regs.get(dbg_status)
        #print "STATUS %.8x" % status
        if status == None:
            return None
        x = status & 0x0f
        if not x:
            return None

        for i in range(4):
            if (x >> i) & 1:
                return self.hwdebug[i]
        return None


class i386Mixin(e_i386.i386Module, e_i386.i386RegisterContext, i386WatchMixin):

    def __init__(self):
        # Mixin our i386 envi architecture module and register context
        e_i386.i386Module.__init__(self)
        # FIXME tracer base should inherit from RegisterContext and we should
        # just have to load a register definition!
        e_i386.i386RegisterContext.__init__(self)
        i386WatchMixin.__init__(self)

        self.setMeta('Architecture', 'i386')

    def archGetStackTrace(self):
        self.requireAttached()
        current = 0
        sanity = 1000
        frames = []

        #FIXME make these by register index
        #FIXME make these GPREG stuff! (then both are the same)
        ebp = self.getRegisterByName("ebp")
        eip = self.getRegisterByName("eip")
        frames.append((eip,ebp))

        while ebp != 0 and current < sanity:
            try:
                buf = self.readMemory(ebp, 8)
                ebp,eip = struct.unpack("<LL",buf)
                if frames[-1] == (ebp,eip):
                    break
                frames.append((ebp,eip))
                current += 1
            except:
                break

        return frames

    def platformCall(self, address, args, convention=None):
        buf = ""
        finalargs = []
        saved_regs = self.getRegisters()
        sp = self.getStackCounter()
        pc = self.getProgramCounter()

        for arg in args:
            if type(arg) == types.StringType: # Nicly map strings into mem
                buf = arg+"\x00\x00"+buf    # Pad with a null for convenience
                finalargs.append(sp - len(buf))
            else:
                finalargs.append(arg)

        m = len(buf) % 4
        if m:
            buf = ("\x00" * (4-m)) + buf

        # Args are 
        #finalargs.reverse()
        buf = struct.pack("<%dI" % len(finalargs), *finalargs) + buf

        # Saved EIP is target addr so when we hit the break...
        buf = struct.pack("<I", address) + buf
        # Calc the new stack pointer
        newsp = sp-len(buf)
        # Write the stack buffer in
        self.writeMemory(newsp, buf)
        # Setup the stack pointer
        self.setStackCounter(newsp)
        # Setup the instruction pointer
        self.setProgramCounter(address)
        # Add the magical call-break
        callbreak = breakpoints.CallBreak(address, saved_regs)
        self.addBreakpoint(callbreak)
        # Continue until the CallBreak has been hit
        while not callbreak.endregs:
            self.run()
        return callbreak.endregs

