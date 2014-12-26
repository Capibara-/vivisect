import os
#import json
import time
import weakref
import threading
import traceback
import collections

from binascii import hexlify

# FIXME where do these live?
#import envi.threads as e_threads

# FIXME py27
def guid():
    return hexlify(os.urandom(16)).decode("ascii")

#class EventChan:

    #def __init__(self, chanid):
        #self.q = e_threads.Queue()
        #self.fd = None
        #self.chanid = chanid

    #def __iter__(self):
        #return iter(self.q)

    #def fire(self, evt, evtinfo):


class ImpulseWindow:
    '''
    A fixed size cache used to create an in-memory window of impulses.
    '''
    def __init__(self, maxsize=100000):
        self.has = set()
        self.loc = threading.Lock()
        self.que = collections.deque()

        self.maxsize = maxsize

    def append(self, imp):
        with self.loc:
            if imp[0] in self.has:
                return False
            self.has.add(imp[1])
            self.que.append(imp)
            self._nom_to_the_max()
            return True

    def extend(self, impulses):
        '''
        Add a list of impulses to the window.
        '''
        with self.loc:
            [ self.has.add(imp[1]) for imp in impulses ]
            [ self.que.append(imp) for imp in impulses ]
            self._nom_to_the_max()

    def _nom_to_the_max(self):
        # must be called with self.loc
        quelen = len(self.que)
        if quelen <= self.maxsize:
            return

        # horrid, but *really* fast.
        [ self.has.remove( self.que.popleft()[1] ) for x in xrange( quelen - self.maxsize ) ]

class Synapse:
    '''
    Synapse event distribution.

    "impulse" - an event flowing through the system
                [ guid, pathway, evt, evtinfo ]
    "pathway" - a named group of impulse types ( for subscription )
    "channel" - an instance of a subscriber recieving impulses
    '''
    def __init__(self):
        self.impwin = ImpulseWindow()
        self.synlock = threading.Lock()

        self.isshut = False
        self.shutlock = threading.Lock()

        self.fireq = e_threads.EnviQueue()
        self.synthr = self._fireSynThread()

        self.chans = {}
        self.peers = []
        self.paths = weakref.WeakValueDictionary()
        self.pathlock = threading.Lock()

    #def formSynapticLink(self, synapse):
    #def initImpulsePath(self, path, xmitonly=False):

    @e_threads.firethread
    def _fireSynThread(self):
        for imp,skip in self.fireq:

            # send the impulse to all chans subscribed to the pathway
            [ chan[1].put(imp) for chan in self.paths.get(imp[1],()) if chan[0] != skip ]

            try:

                for peer in self.peers:
                    # skip the impulse originator
                    if peer[0] == skip:
                        continue

                    peer[1].fireSynImpulse(imp,skip=peer[0])

            except Exception, e:
                traceback.print_exc()
                print('_fireSynThread: %s' % e)

    def fireSynImpulse(self, imp, skip=None):
        # dont re-fire things in the window...
        # ( cheap loop detect etc.. )
        if not self.impwin.append(imp):
            return False

        self.fireq.append( (imp,skip) )

    def newSynImpulse(self, path, evt, **evtinfo):
        self.fireSynImpulse( (guid(),path,evt,evtinfo) )

    def finiSynapse(self):
        with self.shutlock:
            self.isshut = True

        peers = self.peers
        for peer in peers:
            peer[0] = None # chanid = None

        self.fireq.shutdown()
        self.synthr.join()

        [ p[2].join() for p in peers ]

    @e_threads.firethread
    def fireSynPeer(self, synapse):
        thr = threading.currentThread()
        with self.shutlock:
            if self.isshut:
                return

            chanid = synapse.initSynChanId()
            peer = [ chanid, synapse, thr ]
            self.peers.append( peer )

        while peer[0]: # chanid set to None during shutdown
            imps = synapse.iterSynChanId(chanid)

            # he thinks we abandonded the chan...
            if imps == None:
                # FIXME re-join and replay window here...
                chanid = synapse.initSynChanId()
                continue

            [ self.fireSynImpulse( imp, skip=chanid ) for imp in imps ]

        synapse.finiSynChanId(chanid)

    def iterSynChan(self, chan=None):
        if chan == None:
            chan = self.initSynChan()

        cid,que,pth = chan
        for imp in que:
            yield imp

    def initSynChanId(self, paths=None):
        '''
        Initialize a synapse chan and return the id.
        Used to allow remote/cobra based synapse peers.
        '''
        chan = self.initSynChan(paths=paths)
        return chan[0]

    def iterSynChanId(self, chanid, timeout=4):
        '''
        Return the next chunk of impulses for the specified chan id.
        If the chan was closed for "abandonment", returns None.

        ( app layer should re-init and join paths, hopefully still in
          the range of the impulse window... )
        '''
        chan = self.chans.get(chanid)
        return chan[1].get(timeout=timeout)

    def finiSynChanId(self, chanid):
        chan = self.chans.get(chanid)
        if chan != None:
            self.finiSynChan(chan=chan)

    def initSynChan(self, paths=None):
        '''
        Initialize a Synapse channel for the current thread.

        Optionally specify paths to join on creation.
        '''
        chan = getattr(threading.currentThread(),'_syn_chan',None)
        if chan == None:
            chanid = os.urandom(16).encode('hex')
            chan = ( chanid, e_threads.EnviQueue(), {} )

            self.chans[chanid] = chan
            threading.currentThread()._syn_chan = chan

            if paths != None:
                [ self.initSynPath(path, chan=chan) for path in paths ]

        return chan

    def finiSynChan(self, chan=None):
        if chan == None:
            chan = getattr(threading.currentThread(),'_syn_chan',None)
        if chan != None:
            for path in chan[2].keys():
                self.finiSynPath(path,chan=chan)

    def initSynPath(self, path, chan=None):
        '''
        Initialize a synapse "path" on our thread's chan.

        ( causes the synapse to begin delivery of impulses for the path )
        '''
        if chan == None:
            chan = self.initSynChan()

        with self.pathlock:
            pathset = self.paths.get(path)
            if pathset == None:
                pathset = weakref.WeakSet()
                self.paths[path] = pathset
                # this *actually* holds the ref....
                chan[2][path] = pathset
            pathset.add( chan[1] )

    def iterSynPath(self, path, chan=None):
        self.initSynPath(path, chan=chan)
        for imp in self.iterSynChan():
            yield imp

    def finiSynPath(self, path, chan=None):
        # we can fini without the lock...
        if chan == None:
            chan = self.initSynChan()

        # pop the set from our dict and remove our que
        chan[2].pop(path).remove(chan[1])

syn1 = Synapse()

def doit():
    for imp in syn1.iterSynPath('woot'):
        print 'IMP'

t = threading.Thread(target=doit)
t.setDaemon(True)
t.start()
    #syn1.newSynImpulse(

#syn1.initSynPath('woot')
syn1.newSynImpulse('woot','blah',5)
syn1.newSynImpulse('woot','blah',6)
import time
time.sleep(10)
#for imp in syn1.iterSynChan():

#class EventFile:

    #def __init__(self, fd):
        #self.fd = fd

    #def iterRawEvents(self):
        #for line in fd:
            #yield json.loads(line)

    #def iterChanEvents(self, chanid, startid=None):
        #'''
        #Iterate the "cooked" (evt
        #'''

    #def __iter__(self):
        #for line in fd:
            #chan,evtid,evt,evtinfo = json.loads(line)
