'''
A unified width-aware AST implementation in use by envi instr args
as well as the base AST representation for vivisect symboliks.  It
is architected for speed and memory footprint.

Goals:
    * ast storage using python prims ( for mem reduction on huge states )
    * json compatible serialization for the AST state.
    * minimal translation between instr operands and symboliks effects

Each element in the ast consists of a tuple:
( nodetype, nodeinfo, nodewidth, nodekids )
'''
import operator as op

def var(r,w):
    return ("var",r,w,None)

def imm(v,w):
    return ("imm",v,w,None)

def add(a,b,w):
    return ("oper","+",w,[a,b])

def sub(a,b,w):
    return ("oper","-",w,[a,b])

def mul(a,b,w):
    return ("oper","*",w,[a,b])

def shr(a,b,w):
    return ("oper",">>",w,[a,b])

def shl(a,b,w):
    return ("oper","<<",w,[a,b])

def and(a,b,w):
    return ("oper","&",w,[a,b])

def or(a,b,w):
    return ("oper","|",w,[a,b])

def xor(a,b,w):
    return ("oper","^",w,[a,b])

def mem(addr,size):
    return ("mem",None,size,[addr])

def parse(s,width=32):
    pass
