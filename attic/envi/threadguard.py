import types
import threading
import envi.threads as e_threads

def newtg():
    return [ None, threading.Event() ]

class ThreadGuardMeth:
    """
    Callable wrapper for methods which queues to a ThreadGuard.
    """
    def __init__(self, guard, meth):
        self.meth = meth
        self.guard = guard

    def __call__(self, *args, **kwargs):
        tg = e_threads.tlsget('_tg_state',newtg)
        tg[1].clear()

        self.guard._tg_que.append( (tg,self.meth,args,kwargs) )
        tg[1].wait()

        ret = tg[0]
        if isinstance(ret,Exception):
            raise ret

        return ret

class ThreadGuard:
    '''
    Enforce that all calls to the wrapped object come from
    the same thread.
    '''
    def __init__(self, obj):
        self._tg_obj = obj
        self._tg_que = e_threads.EnviQueue()
        self._tg_thr = self._fireGuardThread()

    def _tg_shutdown(self):
        self._tg_que.shutdown()
        self._tg_thr.join()

    @e_threads.firethread
    def _fireGuardThread(self):
        for tg,meth,args,kwargs in self._tg_que:
            try:
                tg[0] = meth(*args,**kwargs)
            except Exception, e:
                tg[0] = e
            tg[1].set()

    def __getattr__(self, name):
        ret = getattr(self._tg_obj,name)
        if isinstance(ret,types.MethodType):
            ret = ThreadGuardMeth(self, ret)
            setattr(self,name,ret)
        return ret
