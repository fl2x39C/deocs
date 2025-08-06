from inspect import isclass,signature,Parameter,ismethod
import inspect
from functools import wraps
from curry import curry
from collections.abc import Iterable
from collections import OrderedDict
from memorize import memorize
from trd import vic_execute

__all__ = ['Stuff','IndexedDict','stuff']

class IndexedDict:
    def __init__(self,data,providers_pos=0,providers=None):
        if isinstance(data,(str,bytes)) or not isinstance(data,Iterable):
            data = [data]
        if isinstance(data,dict):
            self._data = OrderedDict(data)
        else:
            if providers is None:
                self._data = OrderedDict({i:v for i,v in enumerate(data)})
            else:
                od = OrderedDict()
                for i,d in enumerate(data[:providers_pos]):
                    od[i] = d
                for k,v in zip(providers,data[providers_pos:]):
                    od[k] = v
                self._data = od
        
    def __getitem__(self,key):
        if isinstance(key,int):
            return self._data[tuple(self._data.keys())[key]]
        if isinstance(key,slice):
            return self.__class__({k:v for k,v in zip(tuple(self._data.keys())[key],tuple(self._data.values())[key])})
        else:
            return self._data[key]

    def keys(self):
        return self._data.keys()
    
    def values(self):
        return self._data.values()
    
    def items(self):
        return self._data.items()
    
    def __len__(self):
        return len(self._data)
    
    def __iter__(self):
        return iter(self._data.values())
    
    def __next__(self):
        return next(iter(self._data.values()))
    
    def __repr__(self):
        return f"IndexedDict({self._data})"

def _create_faked_func(func):
    if isinstance(func,Stuff):
        raise TypeError("func should not be an instance of Stuff")
    if not callable(func):
        raise TypeError("func should be a callable object")
    
    # 如果传入的是类，则处理其 __init__ 方法
    if isclass(func):
        target = func.__init__
    else:
        target = func
    
    # 获取目标函数的签名
    try:
        sig = signature(target)
    except (ValueError, TypeError):
        # 处理无法获取签名的内置函数
        sig = inspect.Signature()
    
    # 构建新函数的参数列表
    params = []
    for name, param in sig.parameters.items():
        # 保留参数类型（位置参数、关键字参数等）
        new_param = Parameter(
            name=name,
            kind=param.kind,
            default=param.default,
            annotation=param.annotation
        )
        params.append(new_param)
    
    # 创建新函数的签名
    new_sig = sig.replace(parameters=params)
    
    if isclass(func):
        # 创建新类
        class fake:
            __init__=_create_faked_func(target)
            __siganture__ = new_sig
            __name__ = func.__name__
            __doc__ = func.__doc__
            
        return fake

    else:
        # 使用 functools.wraps 复制元数据
        @wraps(target)
        def wrapper(*_, **__):
            return None

        # 保留原始签名
        wrapper.__signature__ = new_sig
        return wrapper

class Stuff: #延迟调用执行
    
    def __init__(self,func,cur = None,bound_stuffs = None):
        self.main_func = func
        if cur is None:
            self.func = _create_faked_func(func)
            self.curried = curry(self.func,is_strict=False,delaied=True)
            self.bound_stuffs = {}
        else:
            self.func = cur.func
            self.curried = cur
            self.bound_stuffs = bound_stuffs or {}
    @classmethod
    def _trans(cls,func_or_instance):
        if isinstance(func_or_instance,cls):
            func_or_instance.delaied = True  # 必须确保 使用延时调用，不然is_ready 直接立即得到函数结果
            return True,func_or_instance
        if hasattr(func_or_instance,'__stuff_transed__'):
            # func_or_instance.__stuff_transed__ = True
            return False,func_or_instance
        if not callable(func_or_instance):
            f = lambda : func_or_instance
            # f.__stuff_transed__ = True
            return False,f
        require_cnt = sum(1 for name,param in signature(func_or_instance).parameters.items() if param.default is Parameter.empty)
        if require_cnt > 0 :
            raise ValueError('func must have default value for all parameters')
        # func_or_instance.__stuff_transed__ = True
        return False,func_or_instance
    @property
    def has_var_keyword(self):
        return any(p.kind == Parameter.VAR_KEYWORD for p in self.sig.parameters.values())
    @property
    def has_var_positional(self):
        return any(p.kind == Parameter.VAR_POSITIONAL for p in self.sig.parameters.values())
    
    @property
    def is_ready(self):
        if self.bound_stuffs:
            return self.curried.is_ready and all(f.is_ready for f in self.bound_stuffs.values())
        return self.curried.is_ready
    
    
    def __getattr__(self, name):
        if name in self.__dict__:
            return self.__dict__[name]
        else:
            return getattr(self.curried, name)
    
    def _validate_providers_keys(self, providers,sep=","):
        """验证参数提供者是否合法"""
        if providers is None:
            return []
        if not isinstance(providers, (list, tuple,str)):
            raise TypeError("providers参数必须是列表或元组或字符串")
        if isinstance(providers, str):
            providers = providers.strip().split(sep)
        providers = [str(p).strip() for p in providers]
        if not providers:
            raise ValueError("providers不能为空")
        
        if any(k in providers for k in self.bound_args):
            raise ValueError(f"providers参数不能包含函数签名中已存在的参数名")
    
        if not self.has_var_keyword:
            for p in providers:
                if p not in self.sig.parameters:
                    raise ValueError(f"参数 {p} 不存在于函数签名中")
        return providers

    @property
    def max_supported_args(self):
        """最大支持参数个数"""
        if self.has_var_positional or self.has_var_keyword:
            return float('inf')
        return len(self.params)
    
    def _validate_providers(self, providers_pos,providers,sep=','):
        """验证位置参数提供者是否合法"""
        if not isinstance(providers_pos, int):
            raise TypeError("providers_pos 参数必须是整数 ")
        if providers_pos < 0:
            raise ValueError("providers_pos 参数必须大于等于0 ")
        
        leisure_cnt = self.max_supported_args - len(self.bound_args)
        if providers_pos > leisure_cnt:
            raise ValueError(f"providers_pos 参数不能大于 {leisure_cnt} ")
        providers = self._validate_providers_keys(providers,sep)
        if len(providers) + providers_pos > leisure_cnt:
            raise ValueError(f"providers  参数个数不能大于 {leisure_cnt - providers_pos} ")
        pos = OrderedDict({f'__stuff_pos_{i}' : None for i in range(providers_pos)})
        ks = OrderedDict({k : None for k in providers})
        result = {'pos':pos,'keys':ks}
        return result

    def fill(self,func,providers_pos=0,providers=None,sep=','):
        """一个函数提供多个参数"""
        func = self._trans(func)[1]
        providers = self._validate_providers(providers_pos,providers,sep)
        if isinstance(func,self.__class__):
            self.bound_stuffs[id(func)] = func
        
        @memorize(duration=3)
        @wraps(func)
        def wrapper():
            result = func()
            return IndexedDict(result,providers_pos = providers_pos,providers = providers['keys'].keys())
        args = []
        if providers['pos']:
            for i in range(providers_pos):
                args.append(lambda i=i : wrapper()[i])

        kws= {}
        if providers['keys']:
            for k in providers['keys'].keys():
                kws[k] = lambda k=k : wrapper()[k]
        self.curried = self.curried(*args,**kws)
        return self
    
    def fill_multi(self,*funcs,param_name=None):
        """多个函数提供同一个参数"""
        if not funcs:
            return self
        cls = self.__class__
        funcs = [cls._trans(f)[1] for f in funcs]
        for func in funcs:
            if isinstance(func,cls):
                self.bound_stuffs[id(func)] = func
        f = lambda : [f() for f in funcs]
        if param_name is None:
            self.curried = self.curried(f)
        else:
            self.curried = self.curried(**{param_name:f})
        return self
    @staticmethod    
    def _get_only_pos_args_name(func):
        return [name for i,(name,param) in enumerate(signature(func).parameters.items() )
                if param.kind == Parameter.POSITIONAL_ONLY
                ]
    
    def _evalate_old(self):
        only_pos_args_name = self._get_only_pos_args_name(self.main_func)
        actual_kwargs = {}
        actual_args = []
        for name,arg in self.bound_args.items():
            if name in only_pos_args_name:
                actual_args.append(arg())
            else:
                actual_kwargs[name] = arg()
        return self.main_func(*actual_args,**actual_kwargs)
    
    def _evalate(self):
        only_pos_args_name = self._get_only_pos_args_name(self.main_func)
        # print(only_pos_args_name)
        actural_kwargs = {}
        actural_args = []
        bounds = self.curried.bound_args.copy()
        l = len(bounds)
        
        @vic_execute(max_workers=l//3+1,use_process=0)
        def compute(v):
            return v()
        
        acturals = compute(bounds.values())
        
        p = self.isclass and hasattr(self.main_func,'__init__')
        q = p or (hasattr(self.main_func,'__self__') and not isclass(self.main_func.__self__))
        it = list(self.params)
        if len(it) == 0:
            z = False
            first_anme = None
            first_bound = None
        else:
            first_anme =it[0]
            first_bound = list(bounds.keys())[0]
            z = first_anme in ('cls','self') and first_bound == first_anme
        # print(z,p,q,first_anme,'#################')
        if (p or z) and first_bound in ('cls','self'):
            pre = None
            for i,name in enumerate(bounds.keys()):
                if name == first_anme:
                    pre = acturals[i]
                    continue
                if name in only_pos_args_name:
                    actural_args.append(pre)
                else:
                    actural_kwargs[name] = pre
                pre = acturals[i]
            if pre is not None:
                if first_anme in only_pos_args_name:
                    actural_args.append(pre)
                else:
                    actural_kwargs[it[len(bounds)]] = pre
            
            if z and not p:
                actural_kwargs[first_anme] = 'NONE'
        else:    
            for i,name in enumerate(bounds.keys()):
                if name in only_pos_args_name:
                    actural_args.append(acturals[i])
                else:
                    actural_kwargs[name] = acturals[i]
                    
            if first_anme in ('self','cls') and first_anme not in bounds.keys() and not p:
                actural_args.insert(0,'NONE')
                
        # print(actural_args,actural_kwargs,'-.-'*30)
        return self.main_func(*actural_args,**actural_kwargs)
        
    @property
    def bound_args(self):
        try:
            return self.curried.bound_args
        except AttributeError:
            return {}
    def __call__(self,*args, **kwargs):
        if not args and not kwargs:
            # if not self.is_ready:
            #     raise ValueError("参数不足")
            return self._evalate()
        cls = self.__class__
        trans = cls._trans
        bound_stuffs = self.bound_stuffs.copy()
        gs = []
        for a in args:
            gs.append(trans(a)[1])
            if isinstance(a,cls):
                bound_stuffs[id(a)] = a
        ks = {}

        for k,v in kwargs.items():
            ks[k] = trans(v)[1]
            if isinstance(v,cls):
                bound_stuffs[id(v)] = v
        new_curried = self.curried(*gs,**ks)
        
        
        
        return cls(self.main_func,new_curried,bound_stuffs)
        
    
    
    def register(self,func=None,param_name=None,sep=",",returnStuff=False):
        """套用在函数上，为目标函数提供参数 param_name ，param_name 可以是列表或元组，也可以是字符串，如果是字符串，则会自动转换为列表。"""
        if func is None:
            return lambda f: self.register(f,param_name,returnStuff)
        
        if returnStuff:
            if not isinstance(func,self.__class__):
                func = stuff(func)
                
        func = self._trans(func)[1]
                
        if param_name is None:
            self.curried = self.curried(func)
        elif isinstance(param_name,str):
            if "," in param_name:
                param_name = [i.strip() for i in param_name.split(sep) if i.strip()]
                self.fill(func,0,param_name)
            else:
                self.curried = self.curried(**{param_name:func})
        elif isinstance(param_name,int):
            self.fill(func,providers_pos=param_name)
        elif isinstance(param_name,(tuple,list)):
            self.fill(func,0,param_name)
        else:
            raise TypeError("param_name 参数类型错误")
        return func
    def register_by(self,func=None,*args,**kwargs):
        """ 所有参数均套用在目标函数上，并返回 func 原函数
            支持了装饰器写法，一次性可填充多个参数
        """
        if func is None:
            return lambda f: self.register_by(f,*args,**kwargs)
        param_name = kwargs.pop('param_name',None)
        func = self._trans(func)[1]
        self.register(func,param_name,returnStuff=False)
        if any([args,kwargs]):
            self.curried = self.curried(*args,**kwargs)
        return func

    def register_stuff(self,func=None,*args,**kwargs):
        """ 套用在目标函数上，若提供参数 param_name,则自动解析参数，并提供给self目标函数。
            余下参数为目标函数提供参数。并返回 stuff 实例。
        """
        if func is None:
            return lambda f: self.register_stuff(f,*args,**kwargs)
        param_name = kwargs.pop('param_name',None)
        if not isinstance(func,self.__class__):
            func = stuff(func)
        func = self._trans(func)[1]
        result = self.register(func,param_name,returnStuff=True)
        return result(*args,**kwargs) if any([args,kwargs]) else result
    
def stuff(func=None,*args,**kwargs):
    if func is None:
        return lambda f: stuff(f,*args,**kwargs)
    return Stuff(func)(*args,**kwargs) if any([args,kwargs]) else Stuff(func)

if __name__ == "__main__":
    
    # t = IndexedDict([1,2,3])
    # print(t[1:2])
    @stuff
    def sub(a,b,c):
        return a-b-c
    
    
    @sub.register
    def getA():
        return 3
    
    @sub.register(param_name=2)
    def getB():
        return 2,1
    
    # print(sub())
    # print(*(v() for v in sub.bound_args.values()),sub.bound_args)
    assert sub() == 0

    @stuff
    def add(a,b,c):
        return f"{a=},{b=},{c=}"
    
    @add.register_stuff(param_name='a')
    def getA():
        return 3
    
    @add.register_stuff(param_name=['b','c'])
    def getbc(b,c):
        return c +1,b +2

    @getbc.register
    def getB():
        return 2
    @getbc.register(param_name='c')
    def getC():
        return 1
    
    # print(getbc(),getA())
    # print(add.bound_args)
    # print(*(a() for a in add.bound_args.values()))
    # print(add())
    print(add())
    assert add() == 'a=3,b=2,c=4'
    
    @stuff
    def add(a,b,c):
        return f"{a=},{b=},{c=}"
        
        
    add.fill_multi(getA,getB,getC,param_name='a')
    
    @add.register_by(c=lambda : 3)
    def getB():
        return 2
    print(add())
    assert add() == 'a=[3, 2, 1],b=2,c=3'
    
    
    @stuff
    def add(a,b,c):
        return f"{a=},{b=},{c=}"
    
    
    c = add(a=10)(c=20)(b=30)() 
    assert c == 'a=10,b=30,c=20' == add(b = 30)(10,20)()
    print(c)
    
    print("1、普通函数测试通过")
    
    class A:
        @stuff
        def add(self,a,b,c):
            return f"{a=},{b=},{c=}"
        
        def getA(self):
            return 3
        
        def getbc(self,b,c):
            return c +1,b +2
        
        def getB(self):
            return 2
        def getC(self):
            return 1
    
    a = A()
    print(a.add.bound_args)
    print(a.add(1,2,3)())
    print(ismethod(a.add),ismethod(a.getB),ismethod(a.add.main_func))
    a.add.fill_multi(a.getA,a.getB,a.getC,param_name='a')
    # print(a.add(1,2)())
    
    print(a.add(c=2,b=3)())
    print("2. 类方法测试通过")
    @stuff
    class C:
        def __init__(self,a,b,c):
            self.args = (a,b,c)

        def __eq__(self, other):
            return self.args == other.args
        def __ne__(self, value):
            return  not self.__eq__(value)
    print(*(i() for i in C(1,2,3,5).bound_args.values()))
    print(C(1,2,3)().args)
    print(C(2,3,4)().args)
    print(C(a=2,c=3,b=4)().args)
    print('3、类测试通过')