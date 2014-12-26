# calling convention constants
CC_REG              = 1 << 0    # argument is stored in a register
CC_STACK            = 1 << 1    # argument is stored on the stack
CC_STACK_INF        = 1 << 2    # all following args are stored on the stack
CC_CALLEE_CLEANUP   = 1 << 3    # callee cleans up the stack
CC_CALLER_CLEANUP   = 1 << 4    # caller cleans up the stack

SYM_SYMBOL      = 0
SYM_FUNCTION    = 1
SYM_SECTION     = 2
SYM_MODULE      = 3
SYM_IMPORT      = 4

RELOC_PTR       = 0     # pointer with suggested base already applied
RELOC_RVA       = 1     # pointer slot containing RVA

# meta-register constants
RMETA_MASK  = 0xffff0000
RMETA_NMASK = 0x0000ffff
