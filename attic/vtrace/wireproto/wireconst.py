import struct

def msgtype(x):
    return struct.unpack('<I',x)[0]

# msg types for vtrace wire protocol
WT_MSG_HELO     = msgtype('helo')
WT_MSG_ARCH     = msgtype('arch')
WT_MSG_PLAT     = msgtype('plat')
WT_MSG_DERP     = msgtype('derp')
WT_MSG_ERRO     = msgtype('erro')
WT_MSG_FILE     = msgtype('file')
WT_MSG_LDIR     = msgtype('ldir')
WT_MSG_ATCH     = msgtype('atch')
WT_MSG_DTCH     = msgtype('dtch')
WT_MSG_EXEC     = msgtype('exec')

def typestr(x):
    return struct.pack('<I',x)

if __name__ == '__main__':
    print('// AUTOGEN FROM vtrace.wireproto.wireconst NO EDITING')
    for l,v in locals().items():
        if l.startswith('WT_'):
            print('#define  %s  0x%.8x // %s' % (l,v,typestr(v)))
