import collections

import envi.pagemap as e_pagemap

from envi.const import *

class SymStore:
    '''
    A simple symbol storage object which may be used with
    a flat set, or hierarchy of symbols.
    '''
    def __init__(self, loader=None):
        self._sym_pagemap = e_pagemap.PageMap()

        self._sym_loaded = False
        self._sym_loader = loader

        self._syms = []
        self._sym_subs = {}
        self._sym_by_addr = {}
        self._sym_by_name = {}

    def _sym_load(self):
        # call the loader callback.
        if self._sym_loader:
            self._add_syms( self._sym_loader() )
        self._sym_loaded = True

    def _sym_loadsub(self, name):
        self._sym_subs.get(name)._sym_load()

    def _add_syms(self, symtups):
        # add symbol tuples to the store.
        for symtup in symtups:
            symva,symsize,symname,symtype = symtup
            symname = symname.lower()

            self._syms.append( symtup )
            self._sym_by_addr[ symva ] = symtup
            self._sym_by_name[ symname ] = symtup

    def _add_sub_sym(self, addr, size, name, symstore):
        # add a "sub" symstore to this one
        symtup = (addr,size,name,SYM_MODULE)

        self._sym_pagemap.put(addr,size,symstore)

        self._add_syms( [symtup] )
        self._sym_subs[name.lower()] = symstore

    def _del_sub_sym(self, name):
        symtup = self._del_sym(name)
        if symtup == None:
            return
        symaddr,symsize,symname,symtype
        self._sym_pagemap.pop(symaddr,symsize)

    def _del_sym(self, name):
        name = name.lower()

        symtup = self._sym_by_name.get(name)
        if symtup == None:
            return None

        symaddr,symsize,symname,symtype = symtup

        self._syms.remove(symtup)
        self._sym_subs.pop(name,None)
        self._sym_by_name.pop(symname,None)
        self._sym_by_addr.pop(symaddr,None)

        return symtup

    def getSymByAddr(self, addr):
        '''
        Return a symbol tuple by address or None.
        (va,size,name,type)
        '''
        if not self._sym_loaded:
            self._sym_load()

        subsym = self._sym_pagemap.get(addr)
        if subsym != None:
            return subsym.getSymByAddr(addr)

        return self._sym_by_addr.get(addr)

    def getSymByName(self, name):
        '''
        Return a symbol tuple by name or None.

        Symbol tuples are structured as:
        (va,size,name,type)

        If name is multipart ( parts devided by "." ) this will resolve
        downward through any sub-resolvers.

        Example:
            symtup = s.getSymByName('kernel32.CreateFileA')
        '''
        if not self._sym_loaded:
            self._sym_load()

        name = name.lower()
        symtup = self._sym_by_name.get(name)
        if symtup != None:
            return symtup

        parts = name.split('.')

        cur = self
        for p in parts[:-1]:
            cur = self._sym_subs.get(p)

        return cur._sym_by_name.get(p[-1])

    def getSymList(self):
        '''
        Retrieve a list of the symbol tuples in the SymStore.
        '''
        if not self._sym_loaded:
            self._sym_load()
        return list(self._syms)

