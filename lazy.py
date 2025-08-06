import re
import inspect
import builtins

__all__ = ['lazy']

# 安全的内置函数白名单
safe_builtins = [
    'abs', 'all', 'any', 'bool', 'bytes', 'chr', 'complex', 'dict', 
    'divmod', 'enumerate', 'filter', 'float', 'format', 'frozenset',
    'hash', 'hex', 'int', 'isinstance', 'issubclass', 'iter', 'len',
    'list', 'map', 'max', 'min', 'next', 'oct', 'ord', 'pow', 'range',
    'repr', 'reversed', 'round', 'set', 'slice', 'sorted', 'str', 'sum',
    'tuple', 'zip', 'print', 'Exception'
]

def lazy(obj, caller_locals=None, caller_globals=None):
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


if __name__ == '__main__':
    # 测试
    def test_func(a, b, c=1):
        return a + b + c
    class TestClass:
        def __init__(self , x, y):
            self.x = x
            self.y = y
        def test_method(self, x, y):
            return self.x + self.y + x + y
    print(lazy(test_func)(1, 2))  # 6
    print(lazy("-> test_func(1, 9,0)")())
    t = TestClass(1, 2)
    print(lazy(t.test_method)(3, 4))  # 11


# ==================== 测试用例 ====================
# if __name__ == '__main__':
    import random
    import time
    
    # 测试 lazy 函数
    print("=== 测试 lazy 函数 ===")
    
    # 测试常量包装
    const_five = lazy(5)
    print(const_five())  # 输出 5
    
    # 测试表达式
    expr = lazy("=> 2 ** 8")
    print(expr())  # 输出 256
    
    # 测试无参lambda
    rand_num = lazy("-> random.randint(1, 100)")
    print(rand_num())  # 输出随机数
    
    # 测试带参函数
    adder = lazy("a, b -> a + b")
    adder_func = adder
    print(adder_func(3, 5))  # 输出 8
    
    # 测试多行函数
    multi_line = lazy("def my_func(x):\n    return x * 2")
    my_func = multi_line()
    print(my_func(10))  # 输出 20
    
    l = lazy(list)
    print(l(range(1,4)))  # 输出 [1, 2, 3]