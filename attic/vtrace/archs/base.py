
class TraceArch:

    archsize = -1
    archname = 'unkn'

    def _arch_init(self):
        pass

    def _arch_watchinit(self, addr, size=4, perms='rw'):
        raise Exception('%s does not implement watchpoints' % self.archname)

    def _arch_watchfini(self, addr):
        raise Exception('%s does not implement watchpoints' % self.archname)
