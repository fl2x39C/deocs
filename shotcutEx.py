
import random
import string
import math
import builtins
import operator
from holder import _ as hd
# import toolz.curried as curried
import re
__all__ = ['_'] + [f"_{i}" for i in range(1,21)]


def _replace_isolated_x(txt, args, fix=0):
    if not args:
        return txt
    
    # 构建映射字典：原始字符串 → 目标字符串（如 {'k0': 'k1', 'k1': 'k2'}）
    mapping = {arg: f'k{i+fix}' for i, arg in enumerate(args)}
    
    # 按长度降序排序（避免短字符串先匹配长字符串的子串）
    sorted_args = sorted(args, key=len, reverse=True)
    # 转义特殊字符并构建正则模式（匹配独立的字符串）
    pattern = r'(?<!\w)(' + '|'.join(re.escape(arg) for arg in sorted_args) + r')(?!\w)'
    
    # 替换函数（查字典返回目标字符串）
    def repl(match):
        return mapping.get(match.group(0), match.group(0))
    
    return re.sub(pattern, repl, txt)
def _random_name(n=14):
    return ''.join(random.choice(string.ascii_lowercase.replace("x","").replace("k","")) for _ in range(n))
def unary_fmap(expr_val,env_val=None):
    def applyier(self):
        nonlocal expr_val,env_val
        cls = self.__class__
        env = env_val.copy() if env_val is not None else {}
        env.update(self.env)
        l,r = self.expr.split(':',1)
        expr = expr_val.expr if isinstance(expr_val,cls) else expr_val
        body = f"({r.strip()})" if self.ix is None else r.strip()
        expr = expr.replace('self',body)
        expr = f"{l} : {expr}"
        return cls(expr,env,self.arity,self.ix)
    return applyier

def fmap(expr_val,env_val=None):
    
    def applyier(self,other):
        nonlocal expr_val,env_val
        cls = self.__class__
        # print(isinstance(expr_val,cls),'11111111111111111111111111111111111111111111111',expr_val)
        env = env_val.copy() if env_val is not None else {}
        env.update(self.env)
        l,r = self.expr.split(':',1)
        body = f"({r.strip()})" if self.ix is None else r.strip()
        
        if isinstance(other,cls):
            l2,r2 = other.expr.split(':',1)
            # print(expr_val,'----000077777777777')
            body2 = f"({r2.strip()})" if other.ix is None else r2.strip()
            expr = expr_val.replace('self',body).replace('other',body2)
            # print(expr,'----0000')
            env.update(other.env)
            l_replaced = l.replace("lambda ","",1).replace(",*_,**__","",1).replace("*_,**__","",1)
            l2_replaced = l2.replace("lambda ","",1).replace(",*_,**__","",1).replace("*_,**__","",1)
            args_l = l_replaced.split(",")
            args_l2 = l2_replaced.split(",")
            if self.ix == other.ix == 0:
                args_l,args_l2 = [i.strip() for i in args_l],[i.strip() for i in args_l2]
                arity = len(args_l) + len(args_l2)
                r = _replace_isolated_x(body,args_l)
                r2 = _replace_isolated_x(body2,args_l2,len(args_l))
                l = _replace_isolated_x(l_replaced,args_l)
                l2 = _replace_isolated_x(l2_replaced,args_l2,len(args_l))
                args = (l + ',' + l2 if l2 and l else (l if l else l2)).split(",")
                expr = expr_val.replace('self',r).replace('other',r2)
                print(f"{l=}")
                print(f"{l2=}")
                print(f"{args=}")
                print(f"{r=}")
                print(f"{r2=}")
                print(f"{expr=}")
                print(f"{self.expr=}")
                print(f"{other.expr=}")
                print(f"{body=}")
                print(f"{body2=}")
                print(f"{expr_val=}")
                print(f"{args_l=}")
                print(f"{args_l2=}")
                print(f"{l_replaced=}")
                print(f"{l2_replaced=}")
                print(f"lambda {', '.join(args)},*_,**__: {expr}")
                print('-.-'*30)
                ix = 0
            else:
                # print(args_l,args_l2)
                args = [i.strip() for i in args_l]
                d = args.append
                _ = [d(i.strip()) for i in args_l2 if i.strip() and i.strip() not in args]
                arity = len(args)
                ix = None
            # print(expr,'----1111')
            expr = f"lambda {', '.join(args)},*_,**__: {expr}"
            # print(expr,'----2222')
            return cls(expr,env,arity,ix)
        else:
            name = _random_name()
            expr = expr_val.replace('self',body).replace('other',name)
            expr = f"{l} : {expr}"
            env[name] = other
            return cls(expr,env,self.arity,self.ix)
    
    return applyier


# attrs = [
#     ('curried',[i for i in dir(curried) if i[0]!='_'] )
#     ,('operator',[i for i in dir(operator) if i[0]!='_'] )
#     ,('math',[i for i in dir(math) if i[0]!='_'] )
#     ,('random',[i for i in dir(random) if i[0]!='_'] )
# ]


# def _get_attr(name):
#     for attr_name,attr_list in attrs:
#         if name in attr_list:
#             return getattr(eval(attr_name),name)
#     return None

class _IndexHolder:
    def __init__(self,expr=None,env=None,arity=1,ix=1):
        i = '' if ix == 0 else ix
        self.expr = expr or f"lambda x{i},*_,**__: x{i}"
        self.env = env or {'math':math,'builtins':builtins,'operator':operator,'random':random}
        self.arity = arity
        self.ix = ix
    @property
    def call(self):
        return eval(self.expr,self.env)
    
    def __str__(self):
        expr = self.expr.replace('lambda ','',1).replace(',*_,**__','',1).replace('*_,**__','',1)
        expr = expr.replace(":"," → ",1)
        for k in self.env.keys():
            expr = expr.replace(k,"{" + k + "}")
        return expr.format(**self.env)

    def __repr__(self):
        return f"{self.__class__.__name__}({self})"
    def __call__(self,*args,**kwargs):
        apply_func = kwargs.pop('apply',None)
        if apply_func is None:
            if not len(args) + len(kwargs) == self.arity:
                raise TypeError(f"Expected {self.arity} arguments, got {len(args) + len(kwargs)}")
            return self.call(*args,**kwargs)
        return apply_func(self.call,*args,**kwargs)
        
    
    __neg__ = unary_fmap("-self")
    __pos__ = unary_fmap("+self")
    __abs__ = unary_fmap("abs(self)")
    __invert__ = unary_fmap("~self")
    __add__ = fmap("self+other")
    __sub__ = fmap("self-other")
    __mul__ = fmap("self*other")
    __truediv__ = fmap("self/other")
    __floordiv__ = fmap("self//other")
    __mod__ = fmap("self%other")
    __pow__ = fmap("self**other")
    __lshift__ = fmap("self<<other")
    __rshift__ = fmap("self>>other")
    __and__ = fmap("self&other")
    __xor__ = fmap("self^other")
    __or__ = fmap("self|other")
    __radd__ = fmap("other+self")
    __rsub__ = fmap("other-self")
    __rmul__ = fmap("other*self")
    __rtruediv__ = fmap("other/self")
    __rfloordiv__ = fmap("other//self")
    __rmod__ = fmap("other%self")
    __rpow__ = fmap("other**self")
    __rlshift__ = fmap("other<<self")
    __rrshift__ = fmap("other>>self")
    __rand__ = fmap("other&self")
    __rxor__ = fmap("other^self")
    __ror__ = fmap("other|self")
    # __matmul__ = fmap("self@other")
    __matmul__ = fmap("isinstance(self,other)")
    __rmatmul__ = fmap("isinstance(other,self)")
    __len__ = unary_fmap("len(self)")
    __lt__ = fmap("self<other")
    __le__ = fmap("self<=other")
    __eq__ = fmap("self==other")
    __ne__ = fmap("self!=other")
    __gt__ = fmap("self>other")
    __ge__ = fmap("self>=other")
    # __bool__ = unary_fmap("bool(self)")
    # __int__ = unary_fmap("int(self)")
    # __float__ = unary_fmap("float(self)")
    # __complex__ = unary_fmap("complex(self)")
    # __hash__ = unary_fmap("hash(self)")
    # __iter__ = unary_fmap("iter(self)")
    # __next__ = unary_fmap("next(self)")
    __contains__ = fmap("other in self")
    __reversed__ = unary_fmap("reversed(self)")
    __round__ = unary_fmap("round(self)")
    __floor__ = unary_fmap("math.floor(self)")
    __ceil__ = unary_fmap("math.ceil(self)")
    __trunc__ = unary_fmap("math.trunc(self)")
    # __getattr__ = unary_fmap("getattr(self,name)")
    # __setattr__ = unary_fmap("setattr(self,name,value)")
    # __delattr__ = unary_fmap("delattr(self,name)")
    # __getitem__ = fmap("self[key]")
    # __setitem__ = fmap("self[key]=value")
    # __delitem__ = fmap("del self[key]")
    # __missing__ = unary_fmap("__missing__(self,key)")
    
    def __getattr__(self, name):
        if name in self.__dict__:
            return self.__dict__[name]
        if name in self.env:
            return self.env[name]
        # if not name[0] == '_':  # 过滤私有属性，不扩展其它属性
        #     result = _get_attr(name)
        #     if result is not None:
        #         return result
        env=self.env.copy()
        attr_name = _random_name()
        env[attr_name] = name
        if self.ix is None:
            return self.__class__(f"lambda x,*_,**__: getattr(x,{attr_name})",env,self.arity,self.ix)
        return self.__class__(f"lambda x{self.ix},*_,**__: getattr(x{self.ix},{attr_name})",env,self.arity,self.ix)
        
    def __getitem__(self, key):
        if callable(key):
            return lambda it,*args,**kwargs: it[key(*args,**kwargs)]
        if isinstance(key,(int,str,slice)):
            if self.ix is None:
                return self.__class__(f"lambda x,*_,**__: x[{key}]",self.env,self.arity,self.ix)
            return self.__class__(f"lambda x{self.ix},*_,**__: x{self.ix}[{key}]",self.env,self.arity,self.ix)
        if isinstance(key,tuple):
            return hd[key]
    
    
    in_ = fmap("self in other")
    not_in = fmap("self not in other")
    rin = fmap("other in self")
    instance_of = fmap("isinstance(self,other)")
    contain = fmap("any(i in self for i in other)")
    contains = fmap("all(i in self for i in other)")
    not_contains = fmap("other not in self")
    and_ = fmap("self and other")
    rand_ = fmap("other and self")
    or_ = fmap("self or other")
    ror_ = fmap("other or self")
    not_ = unary_fmap("not self")


_ = _IndexHolder(ix=0) # 特殊占位符 ，每个_代表不同的的输入参数，与其它 _n 占位符混用时 退化成 _0
_1 = _IndexHolder(ix=1) # 索引占位符，同一个 _1 代表同一个输入参数,数字只是为了区别参数，不是参数具体位置
_2 = _IndexHolder(ix=2)
_3 = _IndexHolder(ix=3)
_4 = _IndexHolder(ix=4)
_5 = _IndexHolder(ix=5)
_6 = _IndexHolder(ix=6)
_7 = _IndexHolder(ix=7)
_8 = _IndexHolder(ix=8)
_9 = _IndexHolder(ix=9)
_10 = _IndexHolder(ix=10)
_11 = _IndexHolder(ix=11)
_12 = _IndexHolder(ix=12)
_13 = _IndexHolder(ix=13)
_14 = _IndexHolder(ix=14)
_15 = _IndexHolder(ix=15)
_16 = _IndexHolder(ix=16)
_17 = _IndexHolder(ix=17)
_18 = _IndexHolder(ix=18)
_19 = _IndexHolder(ix=19)
_20 = _IndexHolder(ix=20)

if __name__ == "__main__":
    f = -_1
    print(f(2)) # -2
    f = _1 + 1
    print(f,f(2)) # 3

    # print(f.expr)
    f = abs(_1)
    print(f(2),f(-1)) # 2
    # print(f.expr)
    f = ~_1
    print(f(2),f(-1)) # -3

    f = _1 + _2 
    # print(f.expr)
    print(f(1,2)) # 3
    # print(f(1,2)) # 4
    # print(f.expr)
    # f = _1 - _2 
    # # print(f.expr)
    # print(f(1,2),f) # -1
    print('-.-'*35)
    f = _1 + _1
    print(f(1),f(2)) # 2

    f = _1 * (_2 + _1)
    print(f(4,2),f) # 7
    f = _1 * _2 + _1
    print(f(4,2),f) # 7 
    
    f = math.floor(_1) + math.ceil(_2)
    print(f(1.5,2.5)) # 3.0
    
    f = _1.in_([1,2,3])
    print(f([1]),f(2),f(4)) # True
    # f = lambda x: _1.if_(x,1,2)
    # print(f(True)(),f(False)()) # 1 2
    f  = reversed(_1)
    print(list(f((1,2))))

    f = _1.upper
    print(f("hello")(),f) # HELLO
    
    f = _1[0:4]
    print(f("hello"),f)
    
    f = _[2]
    print(f([1,2,3,4,5]),f)
    print(_ , _ *3)
    
    f = _ @ str
    print(f(123),f,f("hello"))
    
    print(__all__)
    
    f = _.rin(4)
    print(f([1,23]),f(range(5)),f)
    
    

    print(string.ascii_lowercase.replace("x",""))
    
    print('+.+'*35)
    f = _ + _ * _ + 1
    print(f,f(1,2,4))
    f = _ * _ + _
    print(f,f(2,3,4))
    f = _ @ _ & _ @ str
    print(f,f(2,int,'3'),f('4' ,int,'5'))
    
    f = _.contains([1,2,3])
    print(f)
    print(f([1,2]),f([1]),f([4]),f([1,4,3,2]))
    
    f = _.contain([1,2,3])
    print(f)
    print(f([1,2]),f([1]),f([4]),f([1,4,3,2]))
    
    