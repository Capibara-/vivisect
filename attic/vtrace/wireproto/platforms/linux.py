import vtrace.archs.arm as v_arm
import vtrace.archs.i386 as v_i386
import vtrace.archs.amd64 as v_amd64

import vtrace.platforms.base as v_base
import vtrace.platforms.linux as v_linux
import vtrace.platforms.posix as v_posix

from cStringIO import StringIO

class Linuxi386WireTrace(v_linux.Linuxi386Trace):
    #user_reg_struct = user_regs_i386
    #user_dbg_offset = 252
    #reg_val_mask = 0xffffffff

    def __init__(self, wire):
        self.wire = wire
        v_linux.Linuxi386Trace.__init__(self)
        #vtrace.Trace.__init__(self)
        #v_base.TracerBase.__init__(self)
        #v_posix.ElfMixin.__init__(self)
        #v_i386.i386Mixin.__init__(self)
        #LinuxMixin.__init__(self)

        # Pre-calc the index of the debug regs
        #self.dbgidx = self.archGetRegCtx().getRegisterIndex("debug0")

    # overrides to shunt out linux behaviors...
    def _initLibc(self): pass

    def _ptrace_attach(self, pid):
        self.wire.attach(pid)

    def _wire_readlink(self, path):
        return 'none'

    def _wire_fileopen(self, path):
        return StringIO( self.wire.cat(path) )

    def _wire_filecat(self, path):
        return self.wire.cat(path)

    def _wire_listdir(self, path):
        return self.wire.listdir(path)
