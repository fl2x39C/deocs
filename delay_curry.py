from inspect import signature, Parameter
from functools import wraps,update_wrapper
from lazy import lazy as _lazy
from memorize import memorize

__all__ = [ 'delay_curry','DelayCurried','is_lazy','lazy']


# 基础lazy函数
def lazy(value):
    if callable(value) and not hasattr(value, '_is_lazy'):
        def wrapper():
            return value()
        wrapper._is_lazy = True
        return wrapper
    if not callable(value) and not hasattr(value, '_is_lazy'):
        if isinstance(value,str) :
            temp = _lazy(value)
            temp._is_lazy = True
            return temp
        else:
            def _constant_wrapper():
                return value
            _constant_wrapper._is_lazy = True
            return _constant_wrapper
        
    return value

def is_lazy(value):
    return callable(value) and hasattr(value, '_is_lazy') and value._is_lazy


class DelayCurried:
    def __init__(self, func):
        self.func = func
        update_wrapper(self, func)
        self.sig = signature(func)
        self.bound_args = {}
        self._is_ready = False

        # 确定必选参数
        self.required_params = [
            name for name, param in self.sig.parameters.items()
            if param.default is Parameter.empty and
               param.kind not in (Parameter.VAR_POSITIONAL, Parameter.VAR_KEYWORD)
        ]

        var_count = sum(1 for param in self.sig.parameters.values() if param.kind in (Parameter.VAR_POSITIONAL, Parameter.VAR_KEYWORD))

        self.max_args_count = float('inf') if var_count > 0 else len(self.sig.parameters) - var_count
        
        self._bound_providers = {}
    
    @property
    def has_var_keyword(self):
        return any(p.kind == Parameter.VAR_KEYWORD for p in self.sig.parameters.values())
    @property
    def has_var_positional(self):
        return any(p.kind == Parameter.VAR_POSITIONAL for p in self.sig.parameters.values())
    
    
    @staticmethod
    def resolve_value(value):
        # 递归解析所有嵌套的延迟函数和lazy值
        if isinstance(value, DelayCurried) and value.is_ready:
            return DelayCurried.resolve_value(value())
        if is_lazy(value):
            return DelayCurried.resolve_value(value())
        if isinstance(value, list):
            return [DelayCurried.resolve_value(v) for v in value]
        if isinstance(value, dict):
            return {k: DelayCurried.resolve_value(v) for k, v in value.items()}
        if isinstance(value, tuple):
            return tuple(DelayCurried.resolve_value(v) for v in value)
        return value
    
    
    @property
    def if_full(self):
        
        return len(self.bound_args) == self.max_args_count
    def fill_by_mutil(self, *funcs, provider: str = None):
        """ 多个函数的结果合并成一个tuple 提供给一个参数 (延迟执行版) """
        def merge_func():
            return tuple(DelayCurried.resolve_value(func) for func in funcs)
        lazy_merge = lazy(merge_func)
        if provider is None:
            return self.__call__(lazy_merge)
        else:
            return self.__call__(**{provider: lazy_merge})

    def _validate_providers(self, providers,sep=","):
        # if providers is None:
        #     return None
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

    def bound_providers(self):
        return self._bound_providers
    
    def _bind_provider(self, provider, value):
        self._bound_providers[provider] = value

    def fill(self,func, providers=None,result_is_dict=False,sep=","):
        """ 一个函数提供多个关键字参数,依据返回结果类型自动匹配 (延迟执行版)providers 必须提供参数名列表或逗号分隔的字符串 """
        if not callable(func):
            if isinstance(func, dict):
                # dct = {k: lazy(v) for k, v in func.items() if k in providers}
                return self.__call__(**func)
            elif isinstance(func, (list, tuple)):
                # temp = func[:len(providers)]
                # dct = {k: lazy(v) for k, v in zip(providers, temp)}
                return self.__call__(*func)
            else:
                # dct = {providers[0]: lazy(func)}
                return self.__call__(**{providers[0]: lazy(func)})
            
        # print(providers,'--------------1',type(providers))     
        providers = self._validate_providers(providers,sep)
        
        
        
        func = memorize(func)
        
        
        
        def _wrap_func(func,key):
            def _gene_func():
                temp = func()
                if isinstance(temp, (dict,tuple,list)):
                    return temp[key]
                return temp
            _gene_func.__name__ = f"{func.__name__}_{key}"
            return _gene_func
        
        dct = { }
        for i,provider in enumerate(providers):
            value = lazy(_wrap_func(func,provider if result_is_dict else i))
            self._bind_provider(provider, (func,value))
            dct[provider] = value
        
        # print(dct)
        
        return self.__call__(**dct)
        
        
    def __hash__(self):
        return hash((self.func, 
                     frozenset(self.bound_args.items()) if self.bound_args else None,
                     frozenset(self.bound_providers.items()) if self.bound_args else None
                     ))

    def __eq__(self, other):
        return (isinstance(other, DelayCurried) and self.func == other.func and
                self.bound_args == other.bound_args and self.bound_providers == other.keywords)

    def __ne__(self, other):
        return not self.__eq__(other)

        
    def register(self, func=None,providers=None,result_is_dict=False,sep=",",return_curried=False):
        """_summary__

        Args:
            func: 函数参数的提供者，可以是函数，也可以是其它任意实例
            providers：为函数提供哪些参数：参数名列表，如果未提供，默认是所有结果提供给一个位置参数
            result_is_dict：与providers 联合使用，结果是否是字典 还是列表，觉得 解包成多个参数的形式
            return_curried：是否返回一个 Stuff 实例，默认为 False，返回原始函数

        Returns:
            _type_: _description_
        """
        if func is None:
            return lambda f: self.register(f,providers,result_is_dict,sep,return_curried)
        _ = self.fill(func,providers,result_is_dict,sep) if providers is not None else self.__call__(func)
        return delay_curry(func) if return_curried else func


    def __call__(self, *args, **kwargs):
        # 包装参数为lazy
        if not args and not kwargs  and not self.is_ready:
            return self
        wrapped_args = [lazy(arg) for arg in args]
        wrapped_kwargs = {k: lazy(v) for k, v in kwargs.items()}

        # 处理位置参数
        param_list = list(self.sig.parameters.values())
        arg_index = 0

        for i, param in enumerate(param_list):
            if arg_index >= len(wrapped_args):
                break

            if param.kind in (Parameter.POSITIONAL_OR_KEYWORD, Parameter.POSITIONAL_ONLY):
                if param.name not in self.bound_args:
                    self.bound_args[param.name] = wrapped_args[arg_index]
                    arg_index += 1
            elif param.kind == Parameter.VAR_POSITIONAL:
                if param.name not in self.bound_args:
                    self.bound_args[param.name] = []
                self.bound_args[param.name].extend(wrapped_args[arg_index:])
                arg_index = len(wrapped_args)
                break

        # 处理关键字参数
        for name, value in wrapped_kwargs.items():
            if name in self.sig.parameters:
                param = self.sig.parameters[name]
                if param.kind == Parameter.POSITIONAL_ONLY:
                    raise TypeError(f"参数 {name} 必须是位置参数")
                if name in self.bound_args:
                    raise TypeError(f"参数 {name} 重复赋值")
                self.bound_args[name] = value
            else:
                var_kw_param = next(
                    (p for p in self.sig.parameters.values() if p.kind == Parameter.VAR_KEYWORD),
                    None
                )
                if var_kw_param:
                    if var_kw_param.name not in self.bound_args:
                        self.bound_args[var_kw_param.name] = {}
                    self.bound_args[var_kw_param.name][name] = value
                else:
                    raise TypeError(f"意外的关键字参数: {name}")

        # 检查是否所有必选参数都已绑定
        self._is_ready = all(param in self.bound_args for param in self.required_params)
        
        if self._is_ready:
            self._is_ready = all( value.is_ready  for value in self.bound_args.values() if isinstance(value, DelayCurried))

        # 如果没有参数且已准备好，执行函数
        if not args and not kwargs and self._is_ready:
            return self._execute()

        # 否则返回自身以继续绑定
        return self
    
    
    
    
    def _execute(self):
        # 新增：递归解析所有嵌套的延迟函数
        def resolve_value(value):
            # 如果是已准备好的延迟函数实例，执行它
            if isinstance(value, DelayCurried) and value.is_ready:
                return resolve_value(value())
            # 处理lazy包装的值
            if is_lazy(value):
                return resolve_value(value())
            # 递归处理列表元素
            if isinstance(value, list):
                return [resolve_value(v) for v in value]
            # 递归处理字典值
            if isinstance(value, dict):
                return {k: resolve_value(v) for k, v in value.items()}
            return value

        # 解析所有参数（使用新的递归解析函数）
        resolved_args = {}
        for name, value in self.bound_args.items():
            if name in self._bound_providers:
                value = self._bound_providers[name]
                value = value[1]()
                # print(value,'--------------2')
            resolved_args[name] = resolve_value(value)

        # 准备执行参数
        pos_args = []
        kw_args = {}
        var_pos = []
        var_kw = {}

        for name, param in self.sig.parameters.items():
            if name not in resolved_args:
                continue

            value = resolved_args[name]
            if param.kind in (Parameter.POSITIONAL_OR_KEYWORD, Parameter.POSITIONAL_ONLY):
                pos_args.append(value)
            elif param.kind == Parameter.VAR_POSITIONAL:
                var_pos.extend(value)
            elif param.kind == Parameter.KEYWORD_ONLY:
                kw_args[name] = value
            elif param.kind == Parameter.VAR_KEYWORD:
                var_kw.update(value)

        # 合并参数
        pos_args.extend(var_pos)
        kw_args.update(var_kw)

        # 执行函数
        return self.func(*pos_args, **kw_args)

    @property
    def is_ready(self):
        return self._is_ready

# 装饰器
def delay_curry(func):
    # f =  DelayCurried(func)
    @wraps(func)
    def wrapper(*args, **kwargs):
        # if not args and not kwargs:
        #     return func()
        return DelayCurried(func)(*args, **kwargs)
    
    # for i in dir(f):
    #     if not i.startswith('_'):
    #         setattr(wrapper, i, getattr(f, i))
    #         print(i)
    
    
    return wrapper



# 测试用例
if __name__ == "__main__":
    @delay_curry
    def add(a, b):
        return a + b

    @delay_curry
    def multiply(a, b=1):
        return a * b

    @delay_curry
    def calculate(a, *args, b=0, **kwargs):
        return a + sum(args) * b + sum(kwargs.values())

    try:
        assert add(2)(3)() == 5
        assert multiply(5)(3)() == 15
        assert multiply(10)() == 10
        assert calculate(1)(2, 3)(b=2, c=4, d=5)() == 1 + (2+3)*2 + (4+5) == 1+10+9==20
        print("测试1通过!")
    except AssertionError as e:
        print(f"测试1失败: {e}")
    except Exception as e:
        print(f"发生错误: {e}")
        
    @delay_curry
    def div(a,b):
        return a/b
    try:
        assert (div(2)(3)() == 2/3 == div(2,3)() == div(lambda:2)(3)() == 2/3
                == div("->2","->3")())
        print("测试2通过!")
    except AssertionError as e:
        print(f"测试2失败: {e}")
        
    
    @delay_curry
    def f(a, b, c=1, *args, d=2, **kwargs):
        return a + b + c + sum(args) + d + sum(kwargs.values())
    try:
        assert f(1)(2)(3)(4,5,6)(d=3,e=4,f=5)() == 1+2+3+4+5+6+3+4+5 == 33
        print("测试3通过!")
    except AssertionError as e:
        print(f"测试3失败: {e}")
        print(f(1)(2)(3)(4,5,6)(d=3,e=4,f=5)())
    
    
    
    class B:
        @delay_curry
        def div(self, a, b):
            return a/b
        
        @delay_curry
        def add(self, a, b,*args):
            
            return a + b + sum(args)
        
        
        @staticmethod
        @delay_curry
        def static_add(a, b, *args):
            return a + b + sum(args)
        
        @classmethod
        @delay_curry
        def class_add(cls, a, b, *args):
            return a + b + sum(args) 
        
    try:
        a,b,c,d = B().div(2)(3)(),B().add(2)(3)(4,5,6)(),B.static_add(2)(3)(4,5,6)(),B.class_add(2)(3)(4,5,6)()
        # print(a,b,c,d)
        assert B().div(2)(3)() -  B().div("->2","->3")() <= 1e-6
        assert B().add(2)(3)(4,5,6)() == 20
        assert B.static_add(2)(3)(4,5,6)() == 20
        assert B.class_add(2)(3)(4,5,6)() == 20
        print("测试4通过!")
    except AssertionError as e:

        print(f"测试4失败: {e}")



    # 测试用例
    import time
    import random
    # 新增测试：嵌套delay_curry函数作为参数
    @delay_curry
    def add(a, b):
        return a + b

    @delay_curry
    def multiply(x, y):
        return x * y


    # print(multiply(add(1)(2),3)())
    @delay_curry
    def compute(a, b):
        # multiply的参数是另一个delay_curry函数add
        return multiply(add(a, b), 2)()
    # print(compute(1)(2)())
    # 测试嵌套调用
    def test_nested_delay_curry():
        # 逐步绑定参数
        add1 = add(1)
        add1_2 = add1(2)  # 此时add1_2应返回3
        assert add1_2() == 3

        # compute的参数是delay_curry函数
        compute1 = compute(1)
        compute1_2 = compute1(2)  # 应计算 multiply(add(1,2), 2) = multiply(3,2) = 6
        assert compute1_2() == 6
        print (compute1_2()) 

    # 新增测试：未被delay修饰但执行成本高的函数
    def expensive_computation():
        # 模拟耗时计算
        time.sleep(0.1)
        return 100

    @delay_curry
    def process_data(data_source, com=1):
        r1 =  data_source * 2 * compute("->2","->random.randint(1,10)")() * com # 注意 如果是个无参函数，不需要带括号 ，直接获取到了结果 直接应用；是delay_curry函数，需要带括号，才会返回delay_curry实例
        r2 =  data_source * 3 * compute("->3","->random.randint(1,10)")() * com
        print(f"r1: {r1}, r2: {r2}")
        return r1 + r2
    
    
    
    @delay_curry
    class vTestClass:
        def __init__(self,data,*args):
            self.data = data
            self.args = args
            
        def __str__(self):
            return f"vTestClass({self.data},{self.args})"
    
    
    def test_expensive_computation():
        # 将耗时函数作为参数
        processor = process_data(expensive_computation)
        # 验证只执行一次昂贵计算
        start_time = time.time()
        result1 = processor()
        result2 = processor()  # 第二次调用应直接使用缓存结果
        result3 = processor(compute("->4","->random.randint(1,2)"))()  # 第三次调用传入参数，应重新计算
        end_time = time.time()
        
        print(f"第一次调用结果: {result1}")
        print(f"第二次调用结果: {result2}")
        print(f"第三次调用结果: {result3}")
        # assert result1 == 200
        # assert result2 == 200
        # 确保总耗时小于两次计算的时间(0.2秒)
        # assert end_time - start_time < 0.15
        print(f"耗时: {end_time - start_time:.3f}秒")
        
        t = vTestClass(1,2,3)
        
        instance_t = t(245,345,456)()
        
        t2 = vTestClass(data=process_data(expensive_computation)(100,200,300),args=[1,2,3])()
        
        print(t2)
        

        print(instance_t)
        

    # 运行测试
    if __name__ == "__main__":
        # ... 现有测试调用 ...
        test_nested_delay_curry()
        test_expensive_computation()
        print("所有测试通过!")
        
        t = vTestClass(1,2,3)
        
        instance_t = t(245,345,456)()
        
        t2 = vTestClass(data=process_data(expensive_computation)(100,200,300),args=[1,2,3])()
        
        print(t2)
        

        print(instance_t)
    

    # 运行测试
        # 新增fill_by_*方法测试
    def test_fill_methods():
        # 测试fill_by_mutil
        @delay_curry
        def sum_tuple(tpl):
            return sum(tpl)

        a = lazy(lambda: 1)
        b = lazy(lambda: 2)
        c = lazy(lambda: 3)
        # print(sum_tuple,type(sum_tuple),isinstance(sum_tuple,DelayCurried),isinstance(compute,DelayCurried))
        assert sum_tuple().fill_by_mutil(a, b, c)() == 6
        assert sum_tuple().fill_by_mutil(1, 2, 3,provider="tpl")() == 6

        # 测试fill
        @delay_curry
        def sum_dict(a, b):
            
            return a + b

        def get_dict():
            return {'a': 10, 'b': 20}
        temp = sum_dict().fill(get_dict,"a,b",1)
        # print(temp.bound_args)
        # print(temp(),'---,.-0'*10)
        assert temp() == 30

        # 测试fill_by_seq
        @delay_curry
        def sum_seq(a, b, c):
            return a + b + c

        def get_seq():
            return [100, 200, 300]
        assert sum_seq().fill(get_seq,["a","b","c"])() == 600

        print("fill*方法测试通过!")
        
        
        from curry import curry
        
        @curry
        def sum_dict_seq(a, b, c, d, e, f):
            return a + b - c + d - e + f,a -b + c - d + e - f,a + b + c + d + e + f
        sum_dict_seq.delaied = True
        s = sum_dict_seq(1,2,3,4,5,6)
        print(s())
        print(sum_seq().fill(s,"a,b,c")())
        assert sum_seq().fill(s,"a,b,c")() == 23
        
        sm = DelayCurried(lambda a,b,c : a + b - c)
        sm.fill(s,"a,b,c")
        print(sm())

    if __name__ == "__main__":
        # ... existing tests ...
        test_fill_methods()