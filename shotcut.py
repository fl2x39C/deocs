


from toolz import curry
from functools import partial,wraps,reduce
import re
import operator
import string
import random
from itertools import repeat,count
from holder import _ as hd
from iif import iif
_identify = lambda x,*_,**__:x

__all__ = ['F','flip','apply','_','hd','iif']
class F:
    __slots__ = ('func',)
    def __init__(self, func=_identify, *args, **kwargs):
        self.func = partial(func, *args, **kwargs) if any([args,kwargs]) else func
    
    @property
    def __name__(self):
        try:
            return self.func.__name__
        except AttributeError:
            return 'F<lambda>'
    @__name__.setter
    def __name__(self, name):
        self.func.__name__ = name
    
    @classmethod
    def _compose(cls,f,g):
        f = f.func if isinstance(f, cls) else f
        g = g.func if isinstance(g, cls) else g
        return cls(lambda *args, **kwargs: f(g(*args, **kwargs)))
    
    @classmethod
    def _ensure_callable(cls, f):
        # if isinstance(f, cls):
        #     return f.func
        if  callable(f):
            return f
        if isinstance(f,tuple):
            return cls(*f)
        return cls(f)
    
    def __rshift__(self,g):
        return self.__class__._compose(self._ensure_callable(g), self.func)
    
    def __lshift__(self, g):
        return self.__class__._compose(self.func, self._ensure_callable(g))
    
    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)
    

@curry
def flip(func):
    @wraps(func)
    def f(a,b):
        return func(b,a)
    return f
@curry
def apply(f,args,kwargs):
    return f(*args,**kwargs)

def _random_name(n=14):
    return ''.join(random.choice(string.ascii_lowercase) for _ in range(n))

def fmap(f,sfmt):
    def applyier(self,other):
        fmt = "(%s)" % sfmt.replace("self",self._fmt)
        cls = self.__class__
        if isinstance(other,cls):
            return cls((f,self,other),
                       fmt.replace("other",other._fmt),
                       dict(list(self._fmt_args.items()) + list(other._fmt_args.items())),
                       self._arity + other._arity)
        else:
            call = F(flip(f),other) << F(self)
            name = _random_name()
            return cls(call,
                       fmt.replace("other","%%(%s)r" % name),
                       dict(list(self._fmt_args.items()) + [(name,other)]),
                       self._arity)
    return applyier

class ArityError(TypeError):
    def __str__(self):
        return "{0!r} expected {1} arguments, got {2}".format(*self.args)

def unary_fmap(f,sfmt):
    def applyier(self):
        fmt = "(%s)" % sfmt.replace("self",self._fmt)
        cls = self.__class__
        return cls(F(self) << f,fmt,self._fmt_args,self._arity)
    return applyier




class _ShotCut:
    __slots__ = ('_call', '_fmt', '_fmt_args', '_arity')
    __flipback__ = None
    def __init__(self,call = _identify,fmt = '_',fmt_args = None,arity=1):
        self._call = call
        self._fmt = fmt
        self._fmt_args = fmt_args or {}
        self._arity = arity
    
    def call(self,name,*args,**kwargs):
        return self.__class__(F(lambda f:apply(f,args,kwargs) << operator.attrgetter(name) << F(self)))
    
    def __getattr__(self,name):
        attr_name =_random_name()
        return self.__class__(F(operator.attrgetter(name)) << F(self),
                              "getattr(%s,%%(%s)r)" % (self._fmt,attr_name),
                              dict(list(self._fmt_args.items()) + [(attr_name,name)]),
                              self._arity)
    __expr__  = expr = hd.__expr__
    __lazy__ = lazy = staticmethod(hd.__lazy__)
    def __getitem__(self,key):
        if isinstance(key,self.__class__):
            return self.__class__((operator.getitem,self,key),
                                  "%s[%s]" % (self._fmt,key._fmt),
                                  dict(list(self._fmt_args.items()) + list(key._fmt_args.items())),
                                  self._arity + key._arity)
        # if isinstance(key,tuple):
        f = hd[key]
        item_name = _random_name()
        return self.__class__(F(f) << F(self),
                              "%s[%%(%s)r]" % (self._fmt,item_name),
                              dict(list(self._fmt_args.items()) + [(item_name,key)]),
                              self._arity)
    def __str__(self):
        args = map(''.join,zip(repeat('x'),map(str,count(1)) ))
        l,r = [],self._fmt
        while r.count('_'):
            n = next(args)
            r = r.replace("_",n,1)
            l.append(n)
        r = r % self._fmt_args
        return "{} => {}".format(','.join(l),r)
    
    def __repr__(self):
        return re.sub(r"x\d+","_",str(self).split('=>',1)[1].strip())
    
    def __call__(self,*args):
        if len(args)!= self._arity:
            raise ArityError(self,self._arity,len(args))
        if not isinstance(self._call,tuple):
            return self._call(*args)
        
        f,l,r = self._call
        return f(l(*args[:l._arity]),r(*args[l._arity:]))
        
    __add__ = fmap(operator.add,"self + other")
    __sub__ = fmap(operator.sub,"self - other")
    __mul__ = fmap(operator.mul,"self * other")
    __truediv__ = fmap(operator.truediv,"self / other")
    __floordiv__ = fmap(operator.floordiv,"self // other")
    __mod__ = fmap(operator.mod,"self % other")
    __pow__ = fmap(operator.pow,"self ** other")
    __lshift__ = fmap(operator.lshift,"self << other")
    __rshift__ = fmap(operator.rshift,"self >> other")
    __and__ = fmap(operator.and_,"self & other")
    __or__ = fmap(operator.or_,"self | other")
    __xor__ = fmap(operator.xor,"self ^ other")
    __neg__ = unary_fmap(operator.neg,"-self")
    __pos__ = unary_fmap(operator.pos,"+self")
    __invert__ = unary_fmap(operator.invert,"~self")
    __eq__ = fmap(operator.eq,"self == other")
    __ne__ = fmap(operator.ne,"self != other")
    __lt__ = fmap(operator.lt,"self < other")
    __le__ = fmap(operator.le,"self <= other")
    __gt__ = fmap(operator.gt,"self > other")
    __ge__ = fmap(operator.ge,"self >= other")
    # __bool__ = unary_fmap(bool,"bool(self)")
    # __int__ = unary_fmap(int,"int(self)")
    # __str__ = unary_fmap(str,"str(self)")
    # __float__ = unary_fmap(float,"float(self)")
    # __complex__ = unary_fmap(complex,"complex(self)")
    # __hash__ = unary_fmap(hash,"hash(self)")
    # __len__ = unary_fmap(len,"len(self)")
    __radd__ = fmap(operator.add,"other + self")
    __rsub__ = fmap(operator.sub,"other - self")
    __rmul__ = fmap(operator.mul,"other * self")
    __rtruediv__ = fmap(operator.truediv,"other / self")
    __rfloordiv__ = fmap(operator.floordiv,"other // self")
    __rmod__ = fmap(operator.mod,"other % self")
    __rpow__ = fmap(operator.pow,"other ** self")
    __rlshift__ = fmap(operator.lshift,"other << self")
    __rrshift__ = fmap(operator.rshift,"other >> self")
    __rand__ = fmap(operator.and_,"other & self")
    __ror__ = fmap(operator.or_,"other | self")
    __rxor__ = fmap(operator.xor,"other ^ self")
    __matmul__= fmap(lambda a,b: isinstance(a,b),"self @ other")
    __rmatmul__= fmap(lambda a,b: isinstance(a,b),"other @ self")

_ = _ShotCut()

if __name__ == '__main__':
    f = _[_+1,_*2]
    print(f(3),f)
    f = _[_+1,_*2,_**3]
    print(f(3),f)
    # f = _[_+1][_*2]
    # print(f(3),f)
    f = _[7]

    print(f(range(10)),f)

    f = _[_][_+1]
    print(f(range(10),slice(1,3),0),f)
    f = _[(_+1,_*2,_**3),_[::]]
    print(list(map(f,range(10))),f)
    f = _[_+1,_*2,_**3]
    print(list(map(f,range(10))),f)
    
    f = _[(_+1,_*2,_**3),curry(reduce,operator.add)]
    print(list(map(f,range(10))),f)

    f = _.expr("return _1 * 10 + _2 *3 + _3 /2 ",'indexed',"def")
    print(f(3,2,3),f)
    
    f = _.lazy(" x -> x + 1")
    print(f(3),f)
    
    f = _.upper
    
    print(f("hello")(),f)
    
    f = _.__len__
    print(f("sdfsfd")(),f)

