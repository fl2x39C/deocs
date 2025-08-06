

from typing import Iterable
from functools import reduce,wraps,partial

__all__ = ['f','NONE','_']

from seq import Seq,NONE

_yib = lambda x:isinstance(x, Iterable) and not isinstance(x, (str,bytes,bytearray))
_identify = lambda x : x
_compact = lambda x : x is not None
def _default (x):
    if x is NONE:
        return NONE
    return x
def _pipe(*funcs):
    def _inn(source):
        return reduce(lambda x,f:f(x),funcs,source)
    return _inn

def _compose(*funcs):
    return _pipe(*funcs[::-1])


class F:
    __slots__= ('func',)
    def __init__(self, func=None, *args, **kwargs):
        func = func or _identify
        self.func = partial(func, *args, **kwargs) if any([args,kwargs]) else func
    
    @property
    def __name__(self):
        try:
            return self.func.__name__
        except AttributeError:
            return 'F<lambda>'
    @classmethod
    def _compose(cls,f,g):
        f = f.func if isinstance(f, cls) else f
        g = g.func if isinstance(g, cls) else g
        return cls(_pipe(f,g))
    
    def __ror__(self, other):
        return self.func(other)
    
    def __rlshift__(self, other):
        if isinstance(other, self.__class__):
            return self.__class__._compose(other, self)
        if _yib(other):
            # return Seq(self.func(x) for x in other)
            return [self.func(x) for x in other]
        return self.func(other)
    
    def __rrshift__(self, other):
        if isinstance(other, self.__class__):
            return self.__class__._compose(self, other)
        if _yib(other):
            return [self.func(x) for x in other]
            # return Seq(self.func(x) for x in other)
        return self.func(other)
    def __rshift__(self,other):
        return self.__class__._compose(self, other)
    def __lshift__(self, other):
        return self.__class__._compose(other, self)
    
    def __call__(self, func=None,*args, **kwargs):
        if func is None:
            def _inn(f):
                return self.__class__(f, *args, **kwargs)
            return _inn
        return self.__class__(partial(func, *args, **kwargs))
    
class Ops:
    
    __slots__= ()
    @staticmethod
    @F
    def map(it,*funcs):
        return Seq(it).map(*funcs)
    
    @staticmethod
    @F
    def filter(it,*funcs):
        return Seq(it).filter(*funcs)
    
    @staticmethod
    @F
    def reduce(it,func,init=None):
        return Seq(it).reduce(func,init)
    
    @staticmethod
    @F
    def accum(it,func,initial=None):
        return Seq(it).accum(func,initial)
    @staticmethod
    @F
    def take_while(it,func):
        return Seq(it).take_while(func)
    
    @staticmethod
    @F
    def drop_while(it,func):
        return Seq(it).drop_while(func)
    
    @staticmethod
    @F
    def take(it,n):
        return Seq(it).take(n)
    
    @staticmethod
    @F
    def skip(it,n):
        return Seq(it).skip(n)
    
    @staticmethod
    @F
    def enumerate(it,n=0):
        return Seq(it).enumerate(n)
    
    @staticmethod
    @F
    def zip(it,*its):
        return Seq(it).zip(*its)
    
    @staticmethod
    @F
    def zip_longest(it,*its,fillvalue=None):
        return Seq(it).zip_longest(*its,fillvalue=fillvalue)
    
    @staticmethod
    @F
    def flatten(it):
        return Seq(it).flatten()
    
    @staticmethod
    @F
    def as_list(it):
        return Seq(it).as_list()
    
    @staticmethod
    @F
    def flatmap(it,func = _identify,mode='before' ):
        return Seq(it).flatmap(func,mode)
    
    @staticmethod
    @F
    def flatmap_ex(it,before_func=None,after_func=None):
        return Seq(it).flatmap_ex(before_func,after_func)
    
    @staticmethod
    @F
    def join(it,sep=','):
        return Seq(it).join(sep)
    
    @staticmethod
    @F
    def register(it,func):
        return Seq(it).register(func)
    
    @staticmethod
    @F
    def run(it,func):
        return Seq(it).run(func)
    
    @staticmethod
    @F
    def any(it,func=None):
        return Seq(it).any(func)
    
    @staticmethod
    @F
    def all(it,func=None):
        return Seq(it).all(func)
    
    @staticmethod
    @F
    def find(it,func=None):
        return Seq(it).find(func)
    
    @staticmethod
    @F
    def find_index(it,func=None):
        return Seq(it).find_index(func)
    
    @staticmethod
    @F
    def count_by(it,key=None):
        return Seq(it).count_by(key)
    
    @staticmethod
    @F
    def reduce_by(it,key=None,func=None):
        return Seq(it).reduce_by(key,func)
    
    @staticmethod
    @F
    def group_by(it,key=None):
        return Seq(it).group_by(key)
    
    @staticmethod
    @F
    def grouper(it,n,fillvalue=None):
        return Seq(it).grouper(n,fillvalue)
    
    @staticmethod
    @F    
    def sort_by(it,key=None,reverse=False):
        return Seq(it).sort_by(key,reverse)
    
    @staticmethod
    @F
    def reverse(it):
        return Seq(it).reverse()
    
    @staticmethod
    @F
    def pipe(*funcs):
        return _pipe(*funcs)
    
    @staticmethod
    @F
    def compose(*funcs):
        return _compose(*funcs)     
        
    @staticmethod
    @F
    def do(x,func=print):
        func(x)
        return x
    
    



    
if __name__ == '__main__':
    f = F()
    @f
    def add(x,y=3):
        return x+y
    
    @f
    def do(x,func= print):
        func(x)
        return x
    3 | add | do
    
    Seq(range(10) >> add ).take(5) | do
