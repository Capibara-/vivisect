import envi

class Disasm:
    '''
    An envi disassembler must extend this class.
    '''

    def __init__(self, arch):
        self.arch = arch
        # FIXME put something about modes in here?
        self.archinfo = envi.getArchInfo(arch)

    def parse(self, mem, va):
        '''
        Parse an opcode tuple from the given envi Memory object.
        ( returns None on invalid opcode/memory )

        Opcode tuples have the following form:
            (va,pfx,mnem,opers)

        * va        - virtual address of the instruction
        * flags     - A tuple of opcode prefix strings
        * mnem      - The opcode mnemonic string
        * opers     - A list of envi.ast tuples
        '''
        return None

    def repr(self, op, cpu=None):
        pstr = ''
        opstr = ''

        va,pfx,mnem,opers = op

        if pfx:
            pstr = ','.join(sorted(pfx))

        if opers:
            opstr = ','.join([self.reproper(op,oper,cpu=cpu) for oper in opers])

        return '0x%.8x: %s %s %s' % (va,pstr,mnem,opstr)

    def reproper(self, op, oper, cpu=None):
        return repr(oper)

