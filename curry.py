from inspect import signature, Parameter, isfunction,isclass
from typing import get_type_hints, Any

__doc__ = """提供柯里化功能的装饰器，支持普通函数、实例方法、类方法和静态方法的柯里化。

柯里化是将接受多个参数的函数转换为一系列接受单个参数的函数的过程，
使得函数可以部分应用参数并返回新的函数。

示例:
    >>> @curry
    ... def add(a, b, c):
    ...     return a + b + c
    ...
    >>> add(1)(2)(3)
    6
    >>> add(1, 2)(3)
    6
    >>> add(1)(2, 3)
    6
"""
__all__ = ['curry','Curried','CurryDescriptor']

class CurryDescriptor:
    
    __slots__ = ('func', 'is_strict','delaied','_name','__doc__','pre_attrs')
    
    def __init__(self, func, is_strict,delaied,**pre_attrs):
        self.func = func
        self.is_strict = is_strict
        self.delaied = delaied
        self._name = func.__name__
        self.__doc__ = func.__doc__
        self.pre_attrs = pre_attrs

    @property
    def __name__(self):
        return self._name

    @__name__.setter
    def __name__(self,v):
        self._name = v
    def __get__(self, instance, owner):
        if instance is None:
            return Curried(self.func, is_strict=self.is_strict,delaied =self.delaied,**self.pre_attrs)
        bound_func = self.func.__get__(instance, owner)
        return Curried(bound_func, is_strict=self.is_strict,delaied =self.delaied,**self.pre_attrs)

    def __call__(self, *args, **kwargs):
        return Curried(self.func, is_strict=self.is_strict,delaied =self.delaied,**self.pre_attrs)(*args, **kwargs)

class Curried:
    
    __slots__ = ('func', 'bound_args', 'is_strict','delaied','_name','__doc__'
                 ,'_isclass','f'
                 ,'sig','params','type_hints','required_args')
    
    def __init__(self, func, bound_args=None, is_strict=False,delaied= False,**pre_attrs):
        self.func = func
        self._name = func.__name__
        self._isclass = isclass(func)
        f = func.__init__ if  self._isclass and hasattr(func, '__init__') else func
        self.f = f
        self.bound_args = bound_args  or {}
        self.delaied = delaied # 是否延迟调用
        self.is_strict = is_strict
        
        
        # 预填充属性，避免重复计算 获取参数信息
        self.sig = pre_attrs.get('sig', signature(f))
        self.params = pre_attrs.get('params', self.sig.parameters)
        self.type_hints = pre_attrs.get('type_hints', get_type_hints(f))
        self.required_args = pre_attrs.get( 'required_args', [
            name for name, param in self.params.items()
            if param.default is Parameter.empty
            and param.kind not in (Parameter.VAR_POSITIONAL, Parameter.VAR_KEYWORD)
        ])

    
    
    @property
    def isclass(self):
        return self._isclass
    
    @property    
    def is_ready(self):
        ready = all(name in self.bound_args for name in self.required_args)
        if ready or not self.isclass  :
            return ready
        l = len(self.required_args)
        s = sum(1 for name in self.required_args if name in self.bound_args) + 1
        if s == l:
            return True
        return False
    
    @property
    def is_full(self):
        bounds = [name for name in self.bound_args]
        for name, param in self.params.items():
            if param.kind in (Parameter.VAR_POSITIONAL, Parameter.VAR_KEYWORD):
                return False
            if name not in bounds:
                return False
        return True
        

    @property
    def __name__(self):
        return self._name

    @__name__.setter
    def __name__(self,v):
        self._name = v
    def _check_type(self, name: str, value: Any):
        if name in self.type_hints:
            expected_type = self.type_hints[name]
            if not isinstance(value, expected_type):
                raise TypeError(f"Argument '{name}' expects type {expected_type}, got {type(value)}")

    def _check_return_type(self, result: Any):
        if 'return' in self.type_hints:
            expected_type = self.type_hints['return']
            if not isinstance(result, expected_type):
                raise TypeError(f"Return value expects type {expected_type}, got {type(result)}")
            
    
    def __hash__(self):
        return hash((self.func, 
                     frozenset(self.bound_args.items()) if self.bound_args else None
                     ))

    def __eq__(self, other):
        
        return (isinstance(other, Curried) and self.func == other.func and
                self.bound_args == other.bound_args)

    def __ne__(self, other):
        return not self.__eq__(other) 

    def __call__(self, *args, **kwargs):
        current_bound = self.bound_args.copy()
        new_bindings = {}

        if not args and not kwargs:
            if self.is_ready:
                pos_args = []
                kw_args = {}

                for name, param in self.params.items():
                    if name in current_bound:
                        if param.kind == Parameter.VAR_POSITIONAL:
                            pos_args.extend(current_bound[name])
                        elif param.kind in (Parameter.POSITIONAL_OR_KEYWORD, Parameter.POSITIONAL_ONLY):
                            pos_args.append(current_bound[name])

                for name, param in self.params.items():
                    if name in current_bound:
                        if param.kind == Parameter.KEYWORD_ONLY:
                            kw_args[name] = current_bound[name]
                        elif param.kind == Parameter.VAR_KEYWORD:
                            kw_args.update(current_bound[name])

                result = self.func(*pos_args, **kw_args)
                if self.is_strict:
                    self._check_return_type(result)
                return result
            # return self
            raise TypeError("Too few arguments")

        bindable_params = []
        for name in self.params:
            if name in current_bound:
                continue
            param = self.params[name]
            if param.kind in (Parameter.POSITIONAL_OR_KEYWORD, 
                              Parameter.POSITIONAL_ONLY,
                              Parameter.VAR_POSITIONAL):
                bindable_params.append(name)

        arg_index = 0
        for param_name in bindable_params:
            if arg_index >= len(args):
                break
            param = self.params[param_name]
            if param.kind == Parameter.VAR_POSITIONAL:
                if param_name in new_bindings:
                    new_bindings[param_name].extend(args[arg_index:])
                else:
                    new_bindings[param_name] = list(args[arg_index:])

                if self.is_strict:
                    for val in args[arg_index:]:
                        self._check_type(param_name, val)
                arg_index = len(args)
                break
            else:
                new_bindings[param_name] = args[arg_index]

                if self.is_strict:
                    self._check_type(param_name, args[arg_index])
                arg_index += 1

        if arg_index < len(args):
            raise TypeError(f"Too many positional arguments: expected at most {arg_index}, got {len(args)}")

        for name, value in kwargs.items():
            if name in self.params:
                param = self.params[name]
                if name in current_bound or name in new_bindings:
                    raise TypeError(f"Multiple values for argument '{name}'")
                if param.kind == Parameter.POSITIONAL_ONLY:
                    raise TypeError(f"Argument '{name}' is position-only")
                new_bindings[name] = value

                if self.is_strict:
                    self._check_type(name, value)
            else:
                var_kw_name = next(
                    (n for n, p in self.params.items() if p.kind == Parameter.VAR_KEYWORD), 
                    None
                )
                if var_kw_name:
                    if var_kw_name not in new_bindings:
                        new_bindings[var_kw_name] = {}
                    new_bindings[var_kw_name][name] = value

                    if self.is_strict and var_kw_name in self.type_hints:
                        expected_type = self.type_hints[var_kw_name]
                        if not isinstance(value, expected_type):
                            raise TypeError(
                                f"Keyword argument '{name}' expects type {expected_type}, "
                                f"got {type(value)}"
                            )
                else:
                    raise TypeError(f"Unexpected keyword argument '{name}'")

        updated_bound = {**current_bound, **new_bindings}
        pre_attrs ={
            'sig': self.sig,
            'params': self.params,
            'type_hints': self.type_hints,
            'required_args': self.required_args
        }
        result = self.__class__(self.func, updated_bound, self.is_strict,self.delaied,**pre_attrs)
        if self.delaied:
            return result
        return result() if result.is_ready else result
        # self.bound_args = updated_bound
        # self.is_ready = all(name in self.bound_args for name in self.required_args)
        # return self() if self.is_ready else self  # "不能复用函数对象，所以必须返回新的对象"
        


def _curry(func=None, *, is_strict=False,delaied=False):
    """柯里化装饰器，将函数转换为可部分应用参数的柯里化函数。

    支持普通函数、实例方法、类方法和静态方法的柯里化。对于实例方法，
    会自动处理`self`参数的绑定，无需手动传递。

    参数:
        func: 要柯里化的函数，如果为None，则返回一个带参数的装饰器。
        is_strict (bool): 是否严格校验参数类型。


    返回:
        Curried: 柯里化后的函数对象，或带参数的装饰器（当func为None时）。

    示例:
        装饰普通函数:
        >>> @curry
        ... def multiply(a, b, c):
        ...     return a * b * c
        ...
        >>> multiply(2)(3)(4)
        24
        >>> multiply(2, 3)(4)
        24

        装饰实例方法:
        >>> class Calculator:
        ...     @curry
        ...     def add(self, a, b):
        ...         return self.value + a + b
        ...
        ...     def __init__(self, value):
        ...         self.value = value
        ...
        >>> calc = Calculator(10)
        >>> add5 = calc.add(5)
        >>> add5(3)
        18

        装饰静态方法:
        >>> class MathUtils:
        ...     @staticmethod
        ...     @curry
        ...     def power(base, exponent):
        ...         return base ** exponent
        ...
        >>> square = MathUtils.power(exponent=2)
        >>> square(3)
        9
    """
    if func is None:
        return lambda f: curry(f, is_strict=is_strict,delaied=delaied)
    # 修复：确保正确导入并使用 isfunction
    if isfunction(func) and '.' in func.__qualname__ and not isinstance(func, (classmethod, staticmethod)):
        return CurryDescriptor(func, is_strict,delaied)
    return Curried(func, is_strict=is_strict,delaied=delaied)



def curry(func=None,*args,**kwargs):
    curry.__doc__ = _curry.__doc__
    is_strict = kwargs.pop('is_strict',False)
    delaied = kwargs.pop('delaied',False)
    if func is None:
        if any([args,kwargs]) :
            lambda f : _curry(f,is_strict=is_strict,delaied=delaied)(*args,**kwargs)
        return lambda f : _curry(f,is_strict=is_strict,delaied=delaied)
    result = _curry(func,is_strict=is_strict,delaied=delaied)
    return result(*args,**kwargs) if any([args,kwargs]) else result
# 测试用例
if __name__ == "__main__":
    
    @curry
    def add(a,b,c):
        return a+b+c
    
    assert add(1)(2)(3) == 6 == add(b=2)(a=1)(c=3)
    assert add(1,2)(3) == 6 == add(1)(2,3)
    assert add(1)(2,3) == 6 == add(1,2,3)
    
    @curry
    def add(a,b,*args,**kwargs):
        return a+b+sum(args)+sum(kwargs.values())
    
    assert add(1,2) == 3 == add(1)(2) == add(1,2,3,-3)
    assert add(1,2,3,4) == 10 == add(1)(2,3,4) == add(c=3,d=4)(1,2)
    def add(a,b,*args,**kwargs):
        return a+b+sum(args)+sum(kwargs.values())
    
    assert curry(add,c=3,d=3)(1,2)  == 9 == curry(add,1,2,3,3) == curry(add,1,2,6) == curry(add,3,6) == curry(add,c=3,d=3)(1)(2)
    
    print("1、普通函数 测试通过 ")
    
    
    class A:
        @curry
        def add(self,a,b,*args,**kwargs):
            return a+b+sum(args)+sum(kwargs.values())
    
        @staticmethod
        @curry
        def static_add(a,b,*args,**kwargs):
            return a+b+sum(args)+sum(kwargs.values())
        
        @classmethod
        @curry
        def cls_add(cls,a,b,*args,**kwargs):
            return a+b+sum(args)+sum(kwargs.values())
    
    a = A()
    assert a.add(1,2) == 3 == a.add(1)(2) == a.add(1,2,3,-3)
    assert a.add(1,2,3,4) == 10 == a.add(1)(2,3,4) == a.add(c=3,d=4)(1,2)
    print("2、实例方法 测试通过 ")
    
    
    assert A.cls_add(1,2) == 3 == A.cls_add(1)(2) == A.cls_add(1,2,3,-3)
    
    print("3、类方法 测试通过 ")
    
    

    assert A.static_add(1,2) == 3 == A.static_add(1)(2) == A.static_add(1,2,3,-3)
    assert A.static_add(1,2,3,4) == 10 == A.static_add(1)(2,3,4) == A.static_add(c=3,d=4)(1,2)
    print("4、静态方法 测试通过 ")
    
    
    @curry
    class B:
        def __init__(self, value,a,b,c,*args):
            self.value = value
            self.args = args + (a,b,c)

        def __eq__(self, other):
            return self.value == other.value and self.args == other.args
        
    # print(B.params)     
    # print()    
    b = B(1,2,3,4)
    
    
    # print(b.value)
    # print(b.args)

    b1 = B(1)(2)(3)(4)
    
    b2 = B(1,2)(3)(4)
    
    b3 = B(1)(2,3)(4)
    
    assert b1 == b2 == b3 == b
    
    @curry
    class C:
        def __init__(self, value,tp):
            self.value = value
            self.tp = tp
        
        def __eq__(self, other):
            return self.value == other.value and self.tp == other.tp
    c1 = C(1,int)
    c2 = C(1)(int)
    assert c1 == c2
    
    
    class C:
        def __init__(self, value,tp):
            self.value = value
            self.tp = tp
        
        def __eq__(self, other):
            return self.value == other.value and self.tp == other.tp
    c1 = curry(C,1,int)
    c2 = curry(C,1)(int)
    c3 = curry(C)(1,int)
    c4 = curry(C)(1)(int)
    assert c1 == c2 == c3 == c4 == C(1,int)
    
    print("5、类测试通过 ")
    
    
    
    @curry
    def add(a,b,c):
        return a+b+c
    
    add.delaied = True
    
    assert add(1)(2,3)() == 6 == add(1,2,3)()  != add(1)(2)(3)
    
    print('6、delaied测试通过')
    
    
    
    @curry(is_strict=True)
    def add(a:str,b:int,c:float)->int:
        return int(a) + b + int(c)
    
    assert add('1')(2)(3.0) == 6 == add('1',2,3.0) == add(b=2,a='1')(c=3.0) 
    
    
    try:
        add(1,2,3)
        assert False
    except TypeError as e:
        print(e)
    
    print('7、strict测试通过')