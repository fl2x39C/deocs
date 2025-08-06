
import math
from functools import reduce
import operator


import re
import inspect
import builtins

__all__ = ['_','lazy','gene_func']

# 安全的内置函数白名单
safe_builtins = [
    'abs', 'all', 'any', 'bool', 'bytes', 'chr', 'complex', 'dict', 
    'divmod', 'enumerate', 'filter', 'float', 'format', 'frozenset',
    'hash', 'hex', 'int', 'isinstance', 'issubclass', 'iter', 'len',
    'list', 'map', 'max', 'min', 'next', 'oct', 'ord', 'pow', 'range',
    'repr', 'reversed', 'round', 'set', 'slice', 'sorted', 'str', 'sum',
    'tuple', 'zip', 'print', 'Exception'
]

def gene_def_func(expr:str, mode='single'):
    """
    生成支持多元参数的函数，使用def定义函数并支持多行表达式
    
    参数:
    expr: 字符串表达式（可多行）
    mode: 
        'single' - 每个独立的 '_' 视为一个参数（按顺序对应）
        'indexed' - 使用 '_n' 格式，数字 n 表示参数位置（n>=1）
    
    返回: 函数对象（函数名为 anonymous_{参数个数}）
    
    注意：必须使用return语句返回表达式的值，否则函数返回None。
        
    # 单行表达式 - 模式1
    f1 = gene_def_func('_ + 2 * _', mode='single')
    print(f1(3, 4))  # 输出: 11
    print(f1.__name__)  # 输出: anonymous_2

    # 单行表达式 - 模式2
    f2 = gene_def_func('_1 + 2 * _2', mode='indexed')
    print(f2(3, 4))  # 输出: 11
    print(f2.__name__)  # 输出: anonymous_2

    # 多行表达式 - 模式1
    f3 = gene_def_func('''if _ > 10:
        return _ * 2
    else:
        return _ + 5''', mode='single')
    print(f3(7,7,7))  # 输出: 12
    print(f3(15,15,15))  # 输出: 30
    print(f3.__name__)  # 输出: anonymous_1

    # 多行表达式 - 模式2
    f4 = gene_def_func('''if _1 > _2:
        return _1 * _3
    else:
        return _2 * _3''', mode='indexed')
    print(f4(5, 10, 2))  # 输出: 20 (10*2)
    print(f4(15, 10, 3))  # 输出: 45 (15*3)
    print(f4.__name__)  # 输出: anonymous_3

    # 无参数函数
    f5 = gene_def_func('return "Hello, World!"')
    print(f5())  # 输出: Hello, World!
    print(f5.__name__)  # 输出: anonymous_0
    """
    # 处理多行表达式
    expr_lines = expr.strip().split('\n')
    indented_expr = '\n'.join(f"    {line}" for line in expr_lines)
    
    if mode == 'single':
        # 模式1: 独立的下划线作为参数
        pattern = r'(?<!\w)_(?!\w)'
        matches = list(re.finditer(pattern, expr))
        num_params = len(matches)
        
        if num_params == 0:
            # 无参函数
            func_name = "anonymous_0"
            func_code = f"def {func_name}():\n{indented_expr}"
            namespace  = {**globals(),**locals()}
            exec(func_code, namespace)
            return namespace[func_name]
        
        # 生成参数名和函数签名
        arg_names = [f'arg{i}' for i in range(num_params)]
        func_signature = ", ".join(arg_names)
        func_name = f"anonymous_{num_params}"
        
        # 替换表达式中的占位符
        parts = []
        last_idx = 0
        for i, match in enumerate(matches):
            start, end = match.span()
            parts.append(expr[last_idx:start])
            parts.append(arg_names[i])
            last_idx = end
        parts.append(expr[last_idx:])
        new_expr = ''.join(parts)
        
        # 处理多行表达式
        new_expr_lines = new_expr.strip().split('\n')
        indented_new_expr = '\n'.join(f"    {line}" for line in new_expr_lines)
        
        # 构建函数代码
        func_code = f"def {func_name}({func_signature}):\n{indented_new_expr}"
        
        namespace  = {**globals(),**locals()}
        exec(func_code, namespace)
        return namespace[func_name]
    
    elif mode == 'indexed':
        # 模式2: 带索引的下划线作为参数
        pattern = r'(?<!\w)_(0*[1-9]\d*)(?!\w)'
        matches = list(re.finditer(pattern, expr))
        
        if not matches:
            # 无参函数
            func_name = "anonymous_0"
            func_code = f"def {func_name}():\n{indented_expr}"
            namespace  = {**globals(),**locals()}
            exec(func_code, namespace)
            return namespace[func_name]
        
        # 提取索引并确定参数数量
        indices = [int(match.group(1)) for match in matches]
        max_index = max(indices)
        num_params = max_index
        
        # 生成参数名和函数签名
        arg_names = [f'arg{i}' for i in range(num_params)]
        func_signature = ", ".join(arg_names)
        func_name = f"anonymous_{num_params}"
        
        # 替换表达式中的占位符
        parts = []
        last_idx = 0
        for match in matches:
            start, end = match.span()
            idx = int(match.group(1)) - 1  # 转换为0-based索引
            
            if idx >= num_params:
                raise ValueError(f"索引 {idx+1} 超出范围，最大参数数为 {num_params}")
            
            parts.append(expr[last_idx:start])
            parts.append(arg_names[idx])
            last_idx = end
        parts.append(expr[last_idx:])
        new_expr = ''.join(parts)
        
        # 处理多行表达式
        new_expr_lines = new_expr.strip().split('\n')
        indented_new_expr = '\n'.join(f"    {line}" for line in new_expr_lines)
        
        # 构建函数代码
        func_code = f"def {func_name}({func_signature}):\n{indented_new_expr}"
        
        namespace  = {**globals(),**locals()}
        exec(func_code, namespace)
        return namespace[func_name]
    
    else:
        raise ValueError(f"无效的模式: {mode}. 请使用 'single' 或 'indexed'")
    


def gene_lambda_func(expr:str, mode='single'):
    """
    生成支持多元参数的函数
    
    参数:
    expr: 字符串表达式
    mode: 
        'single' - 每个独立的 '_' 视为一个参数（按顺序对应）
        'indexed' - 使用 '_n' 格式，数字 n 表示参数位置（n>=1）
    # 模式1: 独立的下划线
    f1 = gene_func('_ + 2 * _', mode='single')
    print(f1(3, 4))  # 11

    f2 = gene_func('_ and _', mode='single')
    print(f2(True, False))  # False

    # 模式2: 带索引的下划线
    f3 = gene_func('_1 + 2*_2', mode='indexed')
    print(f3(3, 4))  # 11

    f4 = gene_func('_1 and _3', mode='indexed')
    print(f4(True, 0, False))  # False

    # 混合模式示例
    f5 = gene_func('_2 and _3 and _1 > 0 and _1 < 10', mode='indexed')
    print(f5(5, True, True))  # True
    返回: lambda 函数
    """
    if mode == 'single':
        # 模式1: 独立的下划线作为参数
        pattern = r'(?<!\w)_(?!\w)'
        matches = list(re.finditer(pattern, expr))
        num_params = len(matches)
        
        if num_params == 0:
            return eval(f'lambda: {expr}',globals(),locals())
        
        arg_names = [f'x{i}' for i in range(num_params)]
        
        parts = []
        last_idx = 0
        for i, match in enumerate(matches):
            start, end = match.span()
            parts.append(expr[last_idx:start])
            parts.append(arg_names[i])
            last_idx = end
        parts.append(expr[last_idx:])
        
        new_expr = ''.join(parts)
        lambda_str = f'lambda {", ".join(arg_names)}: {new_expr}'
        return eval(lambda_str,globals(),locals())
    
    elif mode == 'indexed':
        # 模式2: 带索引的下划线作为参数
        pattern = r'(?<!\w)_(0*[1-9]\d*)(?!\w)'
        matches = list(re.finditer(pattern, expr))
        
        if not matches:
            return eval(f'lambda: {expr}')
        
        indices = [int(match.group(1)) for match in matches]
        max_index = max(indices)
        arg_names = [f'x{i}' for i in range(max_index)]
        
        parts = []
        last_idx = 0
        for match in matches:
            start, end = match.span()
            idx = int(match.group(1)) - 1
            parts.append(expr[last_idx:start])
            parts.append(arg_names[idx])
            last_idx = end
        parts.append(expr[last_idx:])
        
        new_expr = ''.join(parts)
        lambda_str = f'lambda {", ".join(arg_names)}: {new_expr}'
        return eval(lambda_str)
    
    else:
        raise ValueError(f"无效的模式: {mode}. 请使用 'single' 或 'indexed'")
    
    
def gene_func(expr:str, mode='single',func_type='lambda'):
    if func_type == 'lambda':
        return gene_lambda_func(expr, mode)
    elif func_type == 'def':
        return gene_def_func(expr, mode)
    else:
        raise ValueError(f"无效的函数类型: {func_type}. 请使用 'lambda' 或 'def'")
gene_func.__doc__ = f"""
    生成支持多元参数的函数
    func_type : 'lambda' 或 'def', 默认为 'lambda'
    def 模式下 支持 多行表达式
    =============================================================
    {gene_lambda_func.__doc__}
    =============================================================
    {gene_def_func.__doc__}
"""
def _lazy(obj, caller_locals=None, caller_globals=None):
    """
    将输入对象转换为无参函数，支持字符串表达式的解析
    - 对于字符串，解析为函数（支持 -> 和 => 语法）
    - 对于其他对象，返回返回该对象的无参函数
    """
    if callable(obj):
        return obj
    
    if isinstance(obj, str):
        # 处理字符串表达式
        # # 获取调用者作用域
        # safe_globals = caller_globals or globals()
        # safe_locals = caller_locals or locals()
        if caller_globals is None or caller_locals is None:
            try:
                frame = inspect.currentframe().f_back.f_back
                caller_globals = frame.f_globals if frame else globals()
                caller_locals = frame.f_locals if frame else locals()
            except (AttributeError, TypeError):
                caller_globals = globals()
                caller_locals = locals()

        # 处理作用域
        safe_globals = {
            **(caller_globals or {}),
            '__builtins__': {k: getattr(builtins, k) for k in safe_builtins}
        }
        safe_locals = caller_locals or {}
        
    # 处理字符串表达式
        # 创建安全的执行环境
        safe_globals = {
            **caller_globals,
            '__builtins__': {k: getattr(builtins, k) for k in safe_builtins}
        }
        safe_locals = caller_locals
        
        # 规则1：多行函数定义
        if obj.startswith('def '):
            match = re.search(r'def\s+(\w+)\s*\(', obj)
            func_name = match.group(1) if match else '__anonymous__'
            exec(obj, safe_globals, safe_locals)
            func = safe_locals.get(func_name, safe_globals.get(func_name))
            wrapper = lambda: func
            wrapper._is_lazy_wrapper = True
            return wrapper
        
        # 规则2：无参lambda表达式（支持 -> 和 =>）
        if obj.startswith('->') or obj.startswith('=>'):
            expr = obj[2:]
            def _anonymous():
                return eval(expr, safe_globals, safe_locals)
            _anonymous._is_lazy_wrapper = True
            return _anonymous
        
        # 规则3：箭头表达式函数（支持 -> 和 =>）
        arrow_match = re.search(r'(.*?)(->|=>)(.*)', obj)
        if arrow_match:
            left, arrow, right = arrow_match.groups()
            params = [p.strip() for p in left.split(',') if p.strip()]
            func_str = f"def __anonymous({', '.join(params)}):\n    return {right.strip()}"
            exec(func_str, safe_globals, safe_locals)
            wrapper = safe_locals.get('__anonymous')
            
            # wrapper = lambda: func
            wrapper._is_lazy_wrapper = True
            return wrapper
    
    # 规则4：其他类型封装为无参函数
    def _constant_wrapper():
        return obj
    
    _constant_wrapper._is_lazy_wrapper = True
    return _constant_wrapper


# 基础lazy函数
def lazy(value):
    if callable(value) and not hasattr(value, '_is_lazy'):
        def wrapper(*args, **kwargs):
            return value(*args, **kwargs)
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
import operator
import math

def binary_operator(op_func):
    """装饰器用于简化二元运算符方法"""
    def decorator(func):
        def wrapper(self, other):
            if isinstance(other, self.__class__):
                return lambda x, y: op_func(x, y)
            return lambda x: op_func(x, other)
        return wrapper
    return decorator

def unary_operator(op_func):
    """装饰器用于简化一元运算符方法"""
    def decorator(func):
        def wrapper(self):
            return lambda x: op_func(x)
        return wrapper
    return decorator

class SimpleHolder:
    __slots__ = ()
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    # 一元运算符
    @unary_operator(operator.neg)
    def __neg__(self): pass
    
    @unary_operator(operator.pos)
    def __pos__(self): pass
    
    @unary_operator(operator.abs)
    def __abs__(self): pass
    
    @unary_operator(operator.invert)
    def __invert__(self): pass
    
    # 二元运算符
    @binary_operator(operator.add)
    def __add__(self, other): pass
    
    @binary_operator(operator.sub)
    def __sub__(self, other): pass
    
    @binary_operator(operator.mul)
    def __mul__(self, other): pass
    
    @binary_operator(operator.truediv)
    def __truediv__(self, other): pass
    
    @binary_operator(operator.floordiv)
    def __floordiv__(self, other): pass
    
    @binary_operator(operator.mod)
    def __mod__(self, other): pass
    
    @binary_operator(operator.pow)
    def __pow__(self, other): pass
    
    @binary_operator(operator.lshift)
    def __lshift__(self, other): pass
    
    @binary_operator(operator.rshift)
    def __rshift__(self, other): pass
    
    @binary_operator(operator.and_)
    def __and__(self, other): pass
    
    @binary_operator(operator.xor)
    def __xor__(self, other): pass
    
    @binary_operator(operator.or_)
    def __or__(self, other): pass
    
    # 反射运算符
    @binary_operator(lambda a, b: operator.add(b, a))
    def __radd__(self, other): pass
    
    @binary_operator(lambda a, b: operator.sub(b, a))
    def __rsub__(self, other): pass
    
    @binary_operator(lambda a, b: operator.mul(b, a))
    def __rmul__(self, other): pass
    
    @binary_operator(lambda a, b: operator.truediv(b, a))
    def __rtruediv__(self, other): pass
    
    @binary_operator(lambda a, b: operator.floordiv(b, a))
    def __rfloordiv__(self, other): pass
    
    @binary_operator(lambda a, b: operator.mod(b, a))
    def __rmod__(self, other): pass
    
    @binary_operator(lambda a, b: operator.pow(b, a))
    def __rpow__(self, other): pass
    
    @binary_operator(lambda a, b: operator.lshift(b, a))
    def __rlshift__(self, other): pass
    
    @binary_operator(lambda a, b: operator.rshift(b, a))
    def __rrshift__(self, other): pass
    
    @binary_operator(lambda a, b: operator.and_(b, a))
    def __rand__(self, other): pass
    
    @binary_operator(lambda a, b: operator.xor(b, a))
    def __rxor__(self, other): pass
    
    @binary_operator(lambda a, b: operator.or_(b, a))
    def __ror__(self, other): pass
    
    # 特殊运算符
    def __matmul__(self, other): 
        return lambda x: isinstance(x, other)
    
    @unary_operator(len)
    def __len__(self): pass
    
    # 比较运算符
    @binary_operator(operator.lt)
    def __lt__(self, other): pass
    
    @binary_operator(operator.le)
    def __le__(self, other): pass
    
    @binary_operator(operator.eq)
    def __eq__(self, other): pass
    
    @binary_operator(operator.ne)
    def __ne__(self, other): pass
    
    @binary_operator(operator.gt)
    def __gt__(self, other): pass
    
    @binary_operator(operator.ge)
    def __ge__(self, other): pass
    
    # 类型转换
    @unary_operator(bool)
    def __bool__(self): pass
    
    @unary_operator(str)
    def __str__(self): pass
    
    @unary_operator(int)
    def __int__(self): pass
    
    @unary_operator(float)
    def __float__(self): pass
    
    @unary_operator(complex)
    def __complex__(self): pass
    
    @unary_operator(hash)
    def __hash__(self): pass
    
    @unary_operator(iter)
    def __iter__(self): pass
    
    @unary_operator(next)
    def __next__(self): pass
    
    @binary_operator(operator.contains)
    def __contains__(self, item): pass
    
    @unary_operator(reversed)
    def __reversed__(self): pass
    
    def __round__(self, n=None): 
        return lambda x: round(x, n)
    
    @unary_operator(math.floor)
    def __floor__(self): pass
    
    @unary_operator(math.ceil)
    def __ceil__(self): pass
    
    @unary_operator(math.trunc)
    def __trunc__(self): pass
    
    # 属性访问
    def __getattr__(self, name):
        if not isinstance(name, self.__class__):
            return lambda x: getattr(x, name)
        return lambda x, y: getattr(x, y)
    
    def __setattr__(self, name, value):
        if not isinstance(name, self.__class__):
            return lambda x: setattr(x, name, value)
        return lambda x, y, z: setattr(x, y, z)
    
    def __delattr__(self, name):
        if not isinstance(name, self.__class__):
            return lambda x: delattr(x, name)
        return lambda x, y: delattr(x, y)
    
    # 索引访问
    def __getitem__(self, key):
        if isinstance(key, tuple):
            funcs = [self._create_func(item) for item in key]
            def composed(x):
                return reduce(lambda val, f: f(val), funcs, x)
            return composed
        
        if not isinstance(key, self.__class__):
            return lambda x: x[key]
        elif isinstance(key, slice):
            return lambda x: x[key]
        else:
            return lambda x, y: x[y]
    
    def _create_func(self, expr):
        if callable(expr):
            return expr
        elif isinstance(expr, self.__class__):
            return lambda x: x
        elif isinstance(expr, tuple):
            return lambda x: tuple(self._create_func(item)(x) for item in expr)
        elif isinstance(expr, list):
            return lambda x: [self._create_func(item)(x) for item in expr]
        elif isinstance(expr, set):
            return lambda x: {self._create_func(item)(x) for item in expr}
        elif isinstance(expr, dict):
            return lambda x: {k: self._create_func(v)(x) for k, v in expr.items()}
        else:
            return lambda x: expr
    
    def __setitem__(self, key, value):
        if not isinstance(key, self.__class__):
            return lambda x: x.__setitem__(key, value)
        return lambda x, y, z: x.__setitem__(y, z)
    
    def __delitem__(self, key):
        if not isinstance(key, self.__class__):
            return lambda x: x.__delitem__(key)
        return lambda x, y: x.__delitem__(y)
    
    def __missing__(self, key):
        if not isinstance(key, self.__class__):
            return lambda x: x.__missing__(key)
        return lambda x, y: x.__missing__(y)
    
    def __expr__(self, expr, mode='single', func_type='lambda'):
        if callable(expr):
            return expr
        elif isinstance(expr, str):
            return gene_func(expr, mode, func_type)
        else:
            return lambda x: expr
    
    __lazy__ = staticmethod(lazy)
    # 调用处理
    def __call__(self, func=None, *args, **kwargs):
        if func is None:
            if not args and not kwargs:
                return lambda f: f
            return lambda f: lambda x: f(x, *args, **kwargs)
        
        if callable(func):
            return lambda x: func(x, *args, **kwargs)
        
        return lambda x: getattr(x, func)(*args, **kwargs)
    
    
_  = SimpleHolder()

if __name__ == '__main__':
    f = _ + 1

    print(f(2)) # 3

    f = _ @ str

    print(f(2)) # True
    print(f('')) # True

    f = _[_]

    print(f([1,2,3],slice(0,2)))
    
    # f1 = _[_ + 2]  # XXXXXX 不支持 ，必须是元祖
    # print(f1(3))  # 输出: 5 (3+2)
    f1 = _[(_ + 2,)]  # XXXXXX 支持 ，必须是元祖
    print(f1(3),'8888')  # 输出: 5 (3+2)
    
    # 逗号分隔的多表达式切片
    f2 = _[_ + 2, _ * 3]  # 相当于 (x+2)*3
    print(f2(3))  # 输出: 15 ((3+2)*3)
    
    f3 = _[_ * 2, _ + 5]  # 相当于 (x*2)+5
    print(f3(4))  # 输出: 13 ((4 * 2)+5)
    
    # 混合常量和表达式
    f4 = _[10, _ + 1]  # 相当于 (10)+1
    print(f4(100))  # 输出: 11 (忽略输入值)
    
# if __name__ == '__main__':
    # 基础运算
    f = _ +1
    print(f(2))  # 3
    print((_+1)(2))
    # # 类型检查
    print((_ @ str)(2))  # false
    
    # # 简单切片
    print(_[slice(0, 2)]([1, 2, 3, 4]))  # [1, 2]
    
    # # 逗号分隔表达式
    f = _[_ + 2, _ * 3]  # (x+2)*3
    print(f(3))  # 15
    
    # # 混合常量和表达式
    f = _[10, _ + 1]  # 10 + 1
    print(f(100))  # 11
    
    # # 复杂嵌套表达式
    f = _[(_ + 1, _ * 2), _ * 3]  # ((x+1, x*2), x*3)
    print(f(4))  # ((5, 8), 12)
    
    # # 方法调用 (getattr) 非 __xxx__ 方法 必须在添加参数后  调用
    # f = _.__len__  #  无法执行 此操作 
    f = _.upper
    print(f("hello")())  # "HELLO"
    
    f = _.__expr__('_ + 1')
    print(f(2),type(f) )  # 3
    
    
    print(lazy('x -> x-1 + 3')(3))
    
    f = gene_func('_ + 3 * _')
    print(f(2,3))
    
    f = gene_func('_1 + 3 * _1 / _2','indexed')
    print(f(2,3))
    
    f = gene_func('print(_1 + 3 * _1 / _2 , (_ @ str)(_3))','indexed', 'def')
    f(2,3,4)
    f(2,3,'2')
    h = _ 
    f = gene_func('print(_ + 3 * _ / _ , (h @ str)(_))','single', 'def')
    f(1,2,3,4)
    # print(globals())
    
    f = _[_+1,_*2]
    print(f(3),f)
    f = _[7]

    print(f(range(10)),f)
    f = _[(_+1,_*2,_**3)]
    print(list(map(f,range(10))),f)
    f = _[_+1,_*2,_**3]
    print(list(map(f,range(10))),f)
    
    f = _.__lazy__("x->x+3")
    print(f(2))