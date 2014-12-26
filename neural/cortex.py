'''
(basically visgraph 2.0)

neural.cortex is a performance / distributed processing oriented
mathmatical graph.  Extreme care is taken to reduce the memory
footprint and access time for the in-memory graph.
'''

import os
import threading
import collections

from binascii import hexlify

import msgpack
if msgpack.version < (0,4,2):
    raise Exception('neural.cortex requires msgpack>=0.4.2!')

def guid():
    return hexlify(os.urandom(16))

def ldict():
    return collections.defaultdict(list)

def ddict():
    return collections.defaultdict(dict)

def dddict():
    return collections.defaultdict(ddict)

def dldict():
    return collections.defaultdict(ldict)

#def hashable(o):
    #'''Return True if an object is hashable else False'''
    #try:
        #hash(o)
        #return True
    #except TypeError as e:
        #return False

# all graph events *must* be reversable ( and ideally have an inverse event )
graphevents = set([

    'delnode',      # form=<name>, formval=<val>
    'formnode',     # form=<name>, formval=<val>

    'delnodeprop',  # form=<name>, formval=<val>, prop=<name>, oldval=<val>
    'setnodeprop',  # form=<name>, formval=<val>, prop=<name>, oldval=<val>, newval=<val>, index=<idxtype>

    'deledge',      # edgedef=<edgedef>  # (n1form,n1formval,n2form,n2formval,form,formval)
    'formedge',     # edgedef=<edgedef>

    'deledgeprop',  # edgedef=<edgedef>, prop=<name>, oldval=<val>
    'setedgeprop',  # edgedef=<edgedef>, prop=<name>, oldval=<val>, newval=<val>, index=<idxtype>
])

class oneref(collections.defaultdict):
    # make all deserialized strings with the same value
    # into the same string instance by accessing them here.
    def __missing__(self,key):
        self[key] = key
        return key

class Graph:
    '''
    The main mathmatical graph object for cortex.

    All nodes/edges properties may be complex objects, however when
    using graph syncronization and/or incremental change logging they
    must be msgpack compatible.
    '''

    def __init__(self, printer=None):
        self.formlock = threading.Lock()
        self.wipe()

        self.oneref = oneref()
        self.printer = printer

    def wipe(self):
        #self.nodebyid = {}
        #self.edgebyid = {}
        self.formnodes = {}
        self.formedges = {}
        self.edgesbyprop = dddict()
        self.nodesbyprop = dddict()

    def formNode(self, form, valu, ctor=None):
        '''
        Add (or retrieve an existing) node by it's form.

        A node's "form" is the key/value combination which makes
        it unique.  It is expected that upon re-encountering a node
        of the same "form" it is meant to be returned rather than
        being created twice.  A tuple of (key,val) *must* be hashable.

        The optional "ctor" method will be called in the case
        where the node is actually being newly created.

        Example:

            def ctor(node):
                g.setNodeProp(node,'foocount',0)

            node = g.formNode('element','au',ctor=ctor)
            # node now has been added with foocount=0 prop
        '''
        form = self.oneref[form]
        nodedef = (form,valu)
        with self.formlock:

            node = self.formnodes.get(nodedef)
            if node != None:
                return node

            node = ( guid(), {} )
            self.formnodes[nodedef] = node
            self.setNodeProp(node,form,valu)
            self.setNodeProp(node,'form',form)

            if ctor != None:
                ctor(node)

            return node

    def getNodeByForm(self, form, valu):
        '''
        Retrieve a node or None by it's form property.
        '''
        return self.formnodes.get( (form,valu) )

    def getNodesByProp(self, prop, valu=None):
        '''
        Retrieve a list of nodes by property.

        Example:

            for node in g.getNodesByProp('foo',10):
                dostuff(node)
        '''
        if valu != None:
            return self.nodesbyprop.get(prop,{}).get(valu,{}).values()

        ret = []
        for valu,niddict in self.nodesbyprop.get(prop,{}).items():
            ret.extend(niddict.values())
        return ret

    def getEdgesByProp(self, prop, valu=None):
        if valu != None:
            return self.edgesbyprop.get(prop,{}).get(valu,{}).values()

        ret = []
        for valu,eiddict in self.edgesbyprop.get(prop,{}).items():
            ret.extend( eiddict.values() )
        return ret

    def formEdge(self, node1, node2, form, valu, ctor=None):
        '''
        Add (or retrieve an existing) edge by it's form.
        Edges are not uniqd purely by their form properties, but
        rather by their form *and* the nodes which they link.

        Example:
            def ctor( node1, edge, node2 ):
                g.setEdgeProp(edge,'thing',30)

            n1 = g.formNode('foo','bar')
            n2 = g.formNode('foo','baz')

            edge = g.formEdge(n1, n2, 'woot', 30, ctor=ctor)
        '''
        edgedef = ( node1[0], node2[0], form, valu )
        with self.formlock:
            edge = self.formedges.get(edgedef)
            if edge != None:
                return edge

            edge = ( guid(), {} )
            self.formedges[ edgedef ] = edge
            self.setEdgeProp(edge,form,valu)
            self.setEdgeProp(edge,'form',form)
            self.setEdgeProp(edge,'node1',node1[0])
            self.setEdgeProp(edge,'node2',node2[0])
            if ctor != None:
                ctor( node1, edge, node2 )
            return edge

    def setNodeProp(self, node, prop, newval):
        '''
        Set a node property.

        prop    - the property name
        newval  - the property value

        Example:

            node = g.formNode('foo','bar')
            g.setNodeProp(node,'baz',30)

        NOTE: Node properties may be used for later lookup
              of nodes and must therefor be immutable python
              primitives.
        '''
        # short circuit sets of same value
        oldval = node[1].get(prop)
        if newval == oldval:
            return node

        node[1][prop] = newval

        # 0 logic remove is faster even with default dict ctors
        self.nodesbyprop.get(prop,{}).get(oldval,{}).pop(node[0],None)
        self.nodesbyprop[prop][newval][node[0]] = node

        form = node[1].get('form')
        formval = node[1].get(form)

        evtinfo = dict(form=form,formval=formval,prop=prop,newval=newval,oldval=oldval)
        self._fire_event('setnodeprop',evtinfo)

        return node

    def setEdgeProp(self, edge, prop, newval):

        oldval = edge[1].get(prop)
        if newval == oldval:
            return edge

        edge[1][prop] = newval
        # 0 logic remove is faster even with default dict ctors
        self.edgesbyprop.get(prop,{}).get(oldval,{}).pop(edge[0],None)
        self.edgesbyprop[prop][newval][edge[0]] = edge

        return edge

    def syncWithSynapse(self, synapse, pathway):
        '''
        Use a synapse impulse distributor to synchronize realtime graph changes.
        '''

    def setSaveFile(self, fd):
        '''
        Set a file like object to be used in saving graph events.

        NOTE: This must be called *before* changes you wish to save are applied.
        '''
        self.savefd = fd

    def syncSaveFd(self, fd, trunc=True):
        '''
        Copy events from the previously specified savefd to the specified fd.

        NOTE: this is used mostly to facilitate incremental save.
        '''

    def saveToFile(self, fd):
        '''
        Serialize a new copy of the entire graph using graph events into fd.
        '''

    def loadFromFile(self, fd):
        '''
        Load a cortex graph from a file like object full of serialized events.

        NOTE: fd is expected to be open in text mode.
        '''
        unpacker = msgpack.Unpacker(fd,use_list=False)
        for evt,evtinfo in unpacker:
            self._fire_event(evt,evtinfo,local=True)

    #def saveToFile(self, fd):

    # graph event layer, *all* changes must be via this subsystem
    def _fire_event(self, evt, evtinfo, local=False):
        #handler = getattr(self,"_graph_event_%s" 
        #print('GRAPH EVENT: %s %r' % (evt,evtinfo))
        pass

    #def _graph_event_setnodeprop(self, evtinfo):
        #print('EVENT SETNODEPROP %r' % (evtinfo,))

