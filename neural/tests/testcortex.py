import unittest

import neural.cortex as n_cortex

class TestNeural(unittest.TestCase):

    def test_cortex_nodeform(self):
        g = n_cortex.Graph()
        node = g.formNode('woot',20)
        self.assertEqual(node[1].get('woot'),20)
        self.assertEqual(node[1].get('form'),'woot')

        node1 = g.formNode('woot',20)
        node2 = g.formNode('woot',30)

        self.assertEqual(node,node1)
        self.assertNotEqual(node1,node2)

    def test_cortex_nodector(self):
        g = n_cortex.Graph()
        def wootctor(n):
            g.setNodeProp(n,'hehe',30)

        node = g.formNode('woot',10,ctor=wootctor)
        self.assertEqual(node[1].get('hehe'), 30)

    def test_cortex_edgeform(self):
        g = n_cortex.Graph()
        node1 = g.formNode('woot',10)
        node2 = g.formNode('woot',20)

        edge = g.formEdge(node1, node2, 'foo', 'bar')

        self.assertEqual(edge[1].get('foo'),'bar')
        self.assertEqual(edge[1].get('form'),'foo')
        self.assertEqual(edge[1].get('node1'),node1[0])
        self.assertEqual(edge[1].get('node2'),node2[0])

    def test_cortex_edgector(self):
        g = n_cortex.Graph()
        node1 = g.formNode('woot',10)
        node2 = g.formNode('woot',20)

        def fooctor(n1,ed,n2):
            g.setEdgeProp(ed,'lala','blahblah')

        edge = g.formEdge(node1, node2, 'foo', 'bar',ctor=fooctor)
        self.assertEqual(edge[1].get('lala'),'blahblah')

    def test_cortex_nodesbyprop(self):
        g = n_cortex.Graph()
        node1 = g.formNode('woot',10)
        node2 = g.formNode('woot',20)
        node3 = g.formNode('woot',30)

        g.setNodeProp(node1,'getme',8)
        g.setNodeProp(node2,'getme',8)
        g.setNodeProp(node3,'getme',10)

        propnodes = g.getNodesByProp('getme')
        self.assertEqual(len(propnodes),3)
        self.assertIn(node1,propnodes)
        self.assertIn(node2,propnodes)
        self.assertIn(node3,propnodes)

        valnodes = g.getNodesByProp('getme',8)
        self.assertEqual(len(valnodes),2)
        self.assertIn(node1,valnodes)
        self.assertIn(node2,valnodes)
        self.assertNotIn(node3,valnodes)

    def test_cortex_edgesbyprop(self):
        g = n_cortex.Graph()
        node1 = g.formNode('woot',10)
        node2 = g.formNode('woot',20)

        edge1 = g.formEdge(node1, node2, 'foo', 'bar')
        edge2 = g.formEdge(node1, node2, 'foo', 'baz')
        edge3 = g.formEdge(node1, node2, 'foo', 'faz')

        g.setEdgeProp(edge1,'getme',8)
        g.setEdgeProp(edge2,'getme',8)
        g.setEdgeProp(edge3,'getme',10)

        propedges = g.getEdgesByProp('getme')
        self.assertEqual(len(propedges),3)
        self.assertIn(edge1,propedges)
        self.assertIn(edge2,propedges)
        self.assertIn(edge3,propedges)

        valedges = g.getEdgesByProp('getme',8)
        self.assertEqual(len(valedges),2)
        self.assertIn(edge1,valedges)
        self.assertIn(edge2,valedges)
        self.assertNotIn(edge3,valedges)

    def test_cortex_getnodebyform(self):
        g = n_cortex.Graph()
        node1 = g.formNode('woot','toow')
        node2 = g.getNodeByForm('woot','toow')
        self.assertIsNotNone(node2)
        self.assertEqual(node1,node2)
    
    #def test_cortex_getedgebyform(self):

    def test_cortex_oneref(self):
        d = n_cortex.oneref()
        x = "asdf"
        y = b"asdf".decode('ascii') # seperate instances

        a = d[x]
        b = d[y]

        self.assertNotEqual(id(x),id(y))
        self.assertEqual(id(x),id(a))
        self.assertEqual(id(x),id(b))

