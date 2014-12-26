import envi

from ctypes import *

# we want most of the same defs...
from vtrace.platforms.linux import *

if envi.getCurrentPlat() != 'linux':
    raise Exception('vtrace.wires.linux may *only* be imported on linux!')

# linux libc ctypes defs...
libc = CDLL(cutil.find_library("c"))
libc.lseek64.restype = c_ulonglong
libc.lseek64.argtypes = [c_uint, c_ulonglong, c_uint]
libc.read.restype = c_long
libc.read.argtypes = [c_uint, c_void_p, c_long]
libc.write.restype = c_long
libc.write.argtypes = [c_uint, c_void_p, c_long]
libc.ptrace.restype = c_size_t
libc.ptrace.argtypes = [c_int, c_uint32, c_size_t, c_size_t]


#following from Pandaboard ES (OMAP4460) Armv7a (cortex-a9)
class user_regs_arm(Structure):
    _fields_ = (
            ("r0", c_ulong),
            ("r1", c_ulong),
            ("r2", c_ulong),
            ("r3", c_ulong),
            ("r4", c_ulong),
            ("r5", c_ulong),
            ("r6", c_ulong),
            ("r7", c_ulong),
            ("r8", c_ulong),
            ("r9", c_ulong),
            ("r10", c_ulong), #aka 'sl' ?
            ("r11", c_ulong),
            ("r12", c_ulong),
            ("sp", c_ulong),
            ("lr", c_ulong),
            ("pc", c_ulong),
            ("cpsr", c_ulong),
            ("orig_r0", c_ulong),
    )

class fp_reg_arm(Structure):
    _fields_ = (
            ("sign1", c_long, 1),
            ("unused", c_long, 15),
            ("sign2", c_long, 1),
            ("exponent", c_long, 14),
            ("j", c_long, 1),
            ("mantissa1", c_long, 31),
            ("mantissa0", c_long, 32),
    )

class user_fpregs_arm(Structure):
    _fields_ = (
            ("fpregs", fp_reg_arm*8),
            ("fpsr", c_ulong, 32),
            ("fpcr", c_ulong, 32),
            ("ftype", c_ubyte*8),
            ("init_flag", c_ulong),
    )

class USER_arm(Structure):
    _fields_ = (
        ("regs",       user_regs_arm),
        ("u_fpvalid",  c_long),
        ("u_tsize",    c_ulong),
        ("u_dsize",    c_ulong),
        ("u_ssize",    c_ulong),
        ("start_code", c_ulong),
        ("start_stack",c_ulong),
        ("signal",     c_long),
        ("reserved",   c_long),
        ("u_ar0",      c_void_p),
        ("magic",      c_ulong),
        ("u_comm",     c_char*32),
        ("u_debugreg", c_long*8),
        ("fpregs",     user_fpregs_arm),
        ("u_fp0",      c_void_p)
    )

class user_regs_i386(Structure):
    _fields_ = (
        ("ebx",  c_ulong),
        ("ecx",  c_ulong),
        ("edx",  c_ulong),
        ("esi",  c_ulong),
        ("edi",  c_ulong),
        ("ebp",  c_ulong),
        ("eax",  c_ulong),
        ("ds",   c_ushort),
        ("__ds", c_ushort),
        ("es",   c_ushort),
        ("__es", c_ushort),
        ("fs",   c_ushort),
        ("__fs", c_ushort),
        ("gs",   c_ushort),
        ("__gs", c_ushort),
        ("orig_eax", c_ulong),
        ("eip",  c_ulong),
        ("cs",   c_ushort),
        ("__cs", c_ushort),
        ("eflags", c_ulong),
        ("esp",  c_ulong),
        ("ss",   c_ushort),
        ("__ss", c_ushort),
    )


class USER_i386(Structure):
    _fields_ = (
        # NOTE: Expand out the user regs struct so
        #       we can make one call to _rctx_Import
        ("regs",       user_regs_i386),
        ("u_fpvalid",  c_ulong),
        ("u_tsize",    c_ulong),
        ("u_dsize",    c_ulong),
        ("u_ssize",    c_ulong),
        ("start_code", c_ulong),
        ("start_stack",c_ulong),
        ("signal",     c_ulong),
        ("reserved",   c_ulong),
        ("u_ar0",      c_void_p),
        ("u_fpstate",  c_void_p),
        ("magic",      c_ulong),
        ("u_comm",     c_char*32),
        ("debug0",     c_ulong),
        ("debug1",     c_ulong),
        ("debug2",     c_ulong),
        ("debug3",     c_ulong),
        ("debug4",     c_ulong),
        ("debug5",     c_ulong),
        ("debug6",     c_ulong),
        ("debug7",     c_ulong),
    )

class user_regs_amd64(Structure):
    _fields_ = [
        ('r15',      c_uint64),
        ('r14',      c_uint64),
        ('r13',      c_uint64),
        ('r12',      c_uint64),
        ('rbp',      c_uint64),
        ('rbx',      c_uint64),
        ('r11',      c_uint64),
        ('r10',      c_uint64),
        ('r9',       c_uint64),
        ('r8',       c_uint64),
        ('rax',      c_uint64),
        ('rcx',      c_uint64),
        ('rdx',      c_uint64),
        ('rsi',      c_uint64),
        ('rdi',      c_uint64),
        ('orig_rax', c_uint64),
        ('rip',      c_uint64),
        ('cs',       c_uint64),
        ('eflags',   c_uint64),
        ('rsp',      c_uint64),
        ('ss',       c_uint64),
        ('fs_base',  c_uint64),
        ('gs_base',  c_uint64),
        ('ds',       c_uint64),
        ('es',       c_uint64),
        ('fs',       c_uint64),
        ('gs',       c_uint64),
    ]

    def loadCpuRegs(self):
        return { r:getattr(self,r) for (r,t) in self._fields_ }

    def saveCpuRegs(self, regdict):
        pass

intel_dbgregs = (0,1,2,3,6,7)


class PyFilesWire:

    def __init__(self):
        pass

    def listdir(self, path):
        return os.listdir(path)

    def filecat(self, path):
        return file(path,'rb').read()

    def linkread(self, path):
        return os.readlink(path)

    def openfd(self, path, mode='r+b'):
        return file(path,mode)

    #def fileopen(self, path):
        #return file(path,'r+b')

    #def fileread(self, fd, offset, size):
        #fd.seek(offset)
        #return fd.read(size)

    #def filewrite(self, fd, offset, bytez):
        #fd.seek(offset)
        #fd.write(bytez)

regstructs = {
    'amd64':user_regs_amd64,
}

class LinuxWire(PyFilesWire):

    def __init__(self):
        PyFilesWire.__init__(self)
        self.linuxver = self.platver()

        #self.sigpend = collections.deque()

        self.regcls = regstructs.get( self.arch() )
        self.regcache = {}    # cache the ctypes structs

        if self.regcls == None:
            raise Exception('no user_regs_%s ctypes struct def!' % self.arch())

        #if os.getenv('ANDROID_ROOT'):
            #libc = CDLL('/system/lib/libc.so')
        #else:

        self.memfd = None

    def plat(self):
        return 'linux'

    def arch(self):
        return envi.getCurrentArch()

    def platver(self):
        return tuple([ int(v) for v in platform.release().split('-')[0].split('.') ])


    def ptrace(self, code, pid, addr, data):
        """
        The contents of this call are basically cleanly
        passed to the libc implementation of ptrace.
        """
        return libc.ptrace(code, pid, c_size_t(addr), c_size_t(data))

    def memread(self, va, size):
        """
        A *much* faster way of reading memory that the 4 bytes
        per syscall allowed by ptrace
        """
        libc.lseek64(self.memfd, va, 0)
        buf = create_string_buffer(size)
        x = libc.read(self.memfd, addressof(buf), size)
        return buf.raw

    def memwrite(self, va, bytez):
        libc.lseek64(self.memfd, offset, 0)
        x = libc.write(self.memfd, bytez, len(bytez))

    def wait(self, pid):
        pid,status = os.waitpid(pid,0x40000002)
        print "WAIT",pid,status
        return pid,status

    def execute(self, argv):
        pid = os.fork()
        if pid == 0:
            try:
                self.ptrace(PT_TRACE_ME, 0, 0, 0)
                # Make sure our parent gets some cycles
                time.sleep(0.1)
                os.execv(argv[0], argv)
            except Exception, e:
                print('fork bail: %s' % e)
                sys.exit(-1)

        self.ptrace(PT_ATTACH, pid, 0, 0)

        tid,status = self.wait(pid)
        if not os.WIFSTOPPED(status):
            raise Exception('requird WIFESTOPPED')

        sig = WIFSIG(status)
        if sig != SIGSTOP:
            raise Exception('required SIGSTOP')

        self.ptrace_opts(pid)

        # let it run to the "break"
        self.ptrace(PT_CONTINUE, pid, 0, 0)
        tid,status = self.wait(pid)
        if not os.WIFSTOPPED(status):
            raise Exception('requird WIFESTOPPED')

        sig = WIFSIG(status)
        if sig != SIGTRAP:
            raise Exception('required SIGTRAP got: %d' % sig)

        self.memfd = libc.open('/proc/%d/mem' % pid, O_RDWR | O_LARGEFILE, 0755)
        return pid

    #def fileget(self, path):

    #def fileopen(self, path):
        #return libc.open(path, O_RDWR | O_LARGEFILE, 0755)

    def fileread(self, fileno, offset, size):
        libc.lseek64(fileno, offset, 0)
        buf = create_string_buffer(size)
        x = libc.read(fileno, addressof(buf), size)
        return buf.raw

    def _wire_filewrite(self, fileno, offset, bytez):
        libc.lseek64(fileno, offset, 0)
        x = libc.write(fileno, bytez, len(bytez))

    def attach(self, pid):

        # we're already attached, and he's already stopped
        #if self.stopclone.pop(pid,False):
            #self.ptrace_opts(pid)
            #return

        if self.ptrace(PT_ATTACH, pid, 0, 0) != 0:
            libc.perror("PT_ATTACH pid %d failed" % pid)
            raise Exception("attach failed: %s" % pid)

        tid,status = self.wait(pid)
        if not os.WIFSTOPPED(status):
            raise Exception('requird WIFESTOPPED')

        sig = WIFSIG(status)
        if sig != SIGSTOP:
            raise Exception('required SIGSTOP')

        self.ptrace_opts(pid)

        self.memfd = libc.open('/proc/%d/mem' % pid, O_RDWR | O_LARGEFILE, 0755)
        #self.memfd = self.fileopen('/proc/%d/mem' % pid)

        #opts = PT_O_TRACESYSGOOD
        #if platform.release()[:3] in ('2.6','3.0','3.1','3.2'):
            #opts |= PT_O_TRACECLONE | PT_O_TRACEEXIT

        #self.ptrace(PT_SETOPTIONS, pid, 0, opts)
        #self.memfd = libc.open("/proc/%d/mem" % self.pid, O_RDWR | O_LARGEFILE, 0755)

    def detach(self, tids):
        for tid in tids:
            self.ptrace(PT_DETACH,tid,0,0)
            self.regcache.pop(tid,None)

    def stepi(self, tid):
        self.ptrace(PT_STEP, tid, 0, 0)

        tid,status = self.wait(pid)
        if not os.WIFSTOPPED(status):
            raise Exception('requird WIFESTOPPED')

        sig = WIFSIG(status)
        if t != tid:
            raise Exception('stepi: wait got pid: %d (wanted %d)' % (t,tid))
        if sig != SIGTRAP:
            raise Exception('stepi: wait got sig: %d (wanted SIGTRAP)' % (sig,))

    #def _wire_detach(self, pid):
        #self._ptrace_detach(pid)

    def loadregs(self, tid):
        u = self.regcache.get(tid)
        if u == None:
            u = self.regcls()
            self.regcache[tid] = u
        
        #s = self.regcls()
        #u = self.user_reg_struct()
        if self.ptrace(PT_GETREGS, tid, 0, addressof(u)) == -1:
            raise Exception("Error: ptrace(PT_GETREGS...) failed!")
        return u.loadCpuRegs()
        #regs.loadattr(u)

    def _wire_saveregs(self, tid, regs):
        u = self._wire_
        u = self.user_reg_struct()
        # Populate the reg struct with the current values (to allow for
        # any regs in that struct that we don't track... *fs_base*ahem*
        if self.ptrace(PT_GETREGS, tid, 0, addressof(u)) == -1:
            raise Exception("Error: ptrace(PT_GETREGS...) failed!")

        # FIXME hold a ref to the old struct...

        regs.saveattr(u)
        if self.ptrace(PT_SETREGS, tid, 0, addressof(u)) == -1:
            raise Exception("Error: ptrace(PT_SETREGS...) failed!")

    def ptrace_opts(self, tid):
        opts = PT_O_TRACESYSGOOD
        if self.linuxver > (2,6,0):
            opts |= PT_O_TRACECLONE | PT_O_TRACEEXIT | PT_O_TRACEVFORK | PT_O_TRACEFORK

        return self.ptrace(PT_SETOPTIONS, tid, 0, opts)

    def ptrace_event(self, tid):
        p = c_ulong(0)
        if self.ptrace(PT_GETEVENTMSG, tid, 0, addressof(p)) != 0:
            raise Exception('ptrace PT_GETEVENTMSG failed!')
        return p.value

    def kill(self, tid, sig):
        os.kill(tid,sig)

    def _wire_stopall(self, tids):
        print 'STOPALL',tids
        sigs = []
        for tid in tids:
            os.kill(tid,SIGSTOP)

        for tid in tids:
            print "STOPALL WAIT",tid
            pid,status = os.waitpid(tid,0x40000002)
            while pid != 0:
                if os.WIFSTOPPED(status) and WIFSIG(status) == SIGSTOP:
                    break

                sigs.append( (pid,status) )

                pid,status = os.waitpid(tid,0x40000002 | os.WNOHANG)
        print 'STOPALL RET',sigs
        return sigs

    def run(self, pid, sig, tids, cmd=PT_CONTINUE):

        #cmd = PT_CONTINUE
        #if self.modes.get("syscall"):
            #cmd = PT_SYSCALL

        #pid = self.pid
        #sig = self.sig
        #self.sig = None

        if sig == None:
            sig = 0

        #self._wire_run(sig)
        print "RUNNING",cmd,pid,sig
        if self.ptrace(cmd, pid, 0, sig) != 0:
            libc.perror('ptrace PT_CONTINUE failed for pid %d' % pid)
            raise Exception('FIXME BAD NEWS')

        for tid in tids: #self.threads.keys():
            if tid == pid:
                continue

            if self.ptrace(cmd,tid,0,0) != 0:
                libc.perror('ptrace PT_CONTINUE failed for tid %d' % tid)

        #tid,sig = self._wire_wait(-1)
        tid,status = self.wait(-1)
        signals = [ (tid,status) ]
        #if not os.WIFSTOPPED(status):
            #raise Exception('requird WIFESTOPPED')

        # detect this early to remove from threads...
        #skiptid = None
        #if os.WIFEXITED(status):
            #skiptid = skiptid

        # now bail on the rest of them as well...

        othertids = [ t for t in tids if t != tid ]
        signals.extend( self._wire_stopall(othertids) )

        return signals
        #self.sigpend.extend( self._wire_stopall(othertids) )

        #self.gotsignal(tid,status)

