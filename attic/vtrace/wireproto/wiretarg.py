import struct
import socket
import threading

from vtrace.wireproto.wireconst import *

#import vtrace.wireproto.platandroid
import vtrace.wireproto.platforms.linux as vt_wire_linux

class WireError(Exception):
    def __init__(self, errno, errmsg):
        self.errno = errno
        self.errmsg = errmsg
        Exception.__init__(self,'[%d] %s' % (errno,errmsg))

def checkerro(hdr,body):
    if hdr[0] == WT_MSG_ERRO:
        errno = struct.unpack_from('<I',body)[0]
        errmsg = body[4:]
        raise WireError(errno,errmsg)

class WireTarg:
    '''
    The WireTarg class implements the vtrace wire protocol client.
    '''

    def __init__(self):
        self.lck = threading.Lock()
        self.sock = None
        self.targaddr = None

    def recv(self, size):
        b = ''
        while len(b) < size:
            x = self.sock.recv( size - len(b) )
            if not x: raise Exception('SocketClosed')
            b += x
        return b

    def recvmsg(self):
        hdr = struct.unpack('<III',self.recv(12))
        #print('msg: %r (%d)' % (struct.pack('<I',hdr[0]),hdr[2]))
        body = self.recv(hdr[2])
        return hdr,body

    def transmsg(self, mtype, bytez='', flags=0):
        with self.lck:
            hdr = struct.pack('<III',mtype,flags,len(bytez))
            self.sock.sendall( hdr )
            self.sock.sendall( bytez )
            return self.recvmsg()

    def connect(self, host, port):
        with self.lck:
            self.sock = socket.socket()
            self.sock.connect( (host,port) )
            self.targaddr = (host,port)

    def clone(self):
        wire = WireTarg()
        wire.connect( *self.targaddr )
        return wire

    def arch(self):
        hdr,arch = self.transmsg(WT_MSG_ARCH)
        return arch

    def plat(self):
        hdr,plat = self.transmsg(WT_MSG_PLAT)
        return plat

    def cat(self, path):
        '''
        Retrieve / return file bytes from the wiretarg
        '''
        hdr,body = self.transmsg(WT_MSG_FILE,path + '\x00')
        checkerro(hdr,body)
        return body

    def listdir(self, path):
        hdr,body = self.transmsg(WT_MSG_LDIR,path + '\x00')
        checkerro(hdr,body)
        return body[:-1].split('\x00')

    def attach(self, pid):
        atchmsg = struct.pack('<I', pid)
        hdr,body = self.transmsg(WT_MSG_ATCH,atchmsg)
        checkerro(hdr,body)

    def detach(self, pid):
        dtchmsg = struct.pack('<I', pid)
        hdr,body = self.transmsg(WT_MSG_DTCH,dtchmsg)
        checkerro(hdr,body)

wireclasses = {
    ('linux','i386'): vt_wire_linux.Linuxi386WireTrace,
}

def getWireTarg(host,port):
    wire = WireTarg()
    wire.connect(host,port)
    return wire

def getWireTrace(host,port):

    wire = getWireTarg(host,port)
    # so... what've we got?
    plat = wire.plat()
    arch = wire.arch()

    cls = wireclasses.get( (plat,arch) )
    if cls == None:
        raise Exception('WireTrace Needed: %s %s' % (plat,arch))

    return cls(wire)

if __name__ == '__main__':
    import sys
    wire = getWireTarg(sys.argv[1],int(sys.argv[2]))
    print 'ARCH',wire.arch()
    print 'PLAT',wire.plat()
    print 'CAT' ,wire.cat('/etc/passwd')
    print 'LDIR',wire.listdir('/proc')

    #print repr( wire.cat('/proc/16458/cmdline') )
    #print repr( wire.cat('/proc/16458/cmdline') )
    #print repr( wire.cat('/proc/16458/cmdline') )

    #for i in xrange(100):
        #print i
        #x = file('/etc/passwd','rb').read()
        #x = wire.cat('/etc/passwd')

    trace = getWireTrace(sys.argv[1],int(sys.argv[2]))
    trace.attach( int( sys.argv[3] ) )
    #for pid,proc in trace.ps():
        #print '%.8x %s' % (pid,proc.split()[0])
    trace.release()

