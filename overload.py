import inspect
import types
from functools import wraps
from typing import Any, Callable, Optional, List, Tuple, Union, Dict
import typing
"""参数个数相同的情况，*args, **kws 不要指望只靠数据类型 来选择执行的函数"""
__all__ = ['overload','OverloadManager','strict']

def strict(func):
    """严格类型检查装饰器"""
    sig = inspect.signature(func)
    annotations = func.__annotations__
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()
        
        for name, value in bound.arguments.items():
            if name in annotations:
                expected_type = annotations[name]
                if not isinstance(value, expected_type):
                    raise TypeError(
                        f"参数 '{name}' 应为 {expected_type.__name__} 类型，"
                        f"实际传入 {type(value).__name__} 类型"
                    )
        
        return func(*args, **kwargs)
    return wrapper


class OverloadManager:
    """重载管理器类，支持多种匹配模式和优先级控制"""
    def __init__(self, main_func: Optional[Callable] = None, is_strict: bool = False, global_priority: str = 'last'):
        """
        初始化重载管理器
        :param main_func: 主函数
        :param is_strict: 是否使用严格模式（类型检查）
        :param global_priority: 全局优先级 ('first' 或 'last')
        """
        self.overloads: List[Tuple[Callable, Optional[Callable], int, int]] = []
        self.main_func = main_func
        self.is_strict = is_strict
        self.global_priority = global_priority
        self.counter = 0  # 注册计数器，保证注册顺序
        
        if main_func:
            # 为主函数自动创建检查函数并注册
            priority_value = -10**9 if global_priority == 'first' else 10**9
            self.register(main_func, priority=priority_value)
    
    def __get__(self, instance, owner):
        """描述符协议，支持类方法绑定"""
        if instance is None:
            return self
        return types.MethodType(self, instance)
    
    def register(self, func: Optional[Callable] = None, 
                check: Optional[Callable] = None, 
                priority: Optional[int] = None) -> Union[Callable, 'OverloadManager']:
        """注册重载函数（支持作为装饰器使用）"""
        # 装饰器用法：@manager.register 或 @manager.register(priority=1)
        if func is None:
            def decorator(f: Callable) -> Callable:
                self._register_function(f, check, priority)
                return f
            return decorator
        
        # 直接调用注册
        self._register_function(func, check, priority)
        return self
    
    def _register_function(self, func: Callable, 
                          check: Optional[Callable] = None, 
                          priority: Optional[int] = None) -> None:
        """内部注册函数实现"""
        # 设置默认优先级
        if priority is None:
            priority = 0
        
        # 自动创建检查函数（如果未提供）
        if check is None:
            if self.is_strict:
                check = self._create_strict_check(func)
            else:
                # 普通模式使用参数数量检查
                check = self._create_count_check(func)
        
        # 记录注册顺序并保存
        reg_index = self.counter
        self.counter += 1
        self.overloads.append((check, func, priority, reg_index))
        
        # 设置第一个注册的函数为主函数
        if self.main_func is None:
            self.main_func = func
    
    def _create_count_check(self, func: Callable) -> Callable:
        """创建基于参数数量的检查函数"""
        sig = inspect.signature(func)
        params = sig.parameters
        
        # 计算必需参数数量
        min_args = sum(1 for p in params.values()
                      if p.default == p.empty
                      and p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD))
        
        # 处理可变参数
        has_var_args = any(p.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
                      for p in params.values())
        max_args = float('inf') if has_var_args else len(params)
        
        def count_check(args, kwargs):
            arg_count = len(args) + len(kwargs)
            return min_args <= arg_count <= max_args
        
        return count_check
    def _create_strict_check(self, func: Callable) -> Callable:
        """创建严格的类型检查函数，包含详细的错误信息"""
        sig = inspect.signature(func)
        type_hints = func.__annotations__
        params = sig.parameters
        
        def strict_check(args, kwargs):
            # 第一步：验证参数存在性（位置和名称匹配）
            try:
                bound = sig.bind(*args, **kwargs)
                bound.apply_defaults()
            except TypeError as e:
                # 捕获并重新包装错误信息
                return False, f"参数不匹配: {str(e)}"
            
            # 第二步：检查类型是否符合注解
            errors = []
            for name, value in bound.arguments.items():
                if name in type_hints:
                    expected_type = type_hints[name]
                    param = params[name]
                    
                    # 处理可变位置参数 (*args)
                    if param.kind == inspect.Parameter.VAR_POSITIONAL:
                        for i, item in enumerate(value):
                            if not isinstance(item, expected_type):
                                errors.append(
                                    f"位置参数 #{i} (属于*{name}) 类型错误: "
                                    f"期望 {expected_type.__name__}, 实际 {type(item).__name__}"
                                )
                    
                    # 处理可变关键字参数 (**kwargs)
                    elif param.kind == inspect.Parameter.VAR_KEYWORD:
                        for key, item in value.items():
                            if not isinstance(item, expected_type):
                                errors.append(
                                    f"关键字参数 '{key}' (属于**{name}) 类型错误: "
                                    f"期望 {expected_type.__name__}, 实际 {type(item).__name__}"
                                )
                    
                    # 处理普通参数
                    else:
                        # 检查字典类型的键值对
                        if isinstance(value, dict) and hasattr(expected_type, '__args__'):
                            origin_type = getattr(typing, 'get_origin', None)
                            if origin_type and origin_type(expected_type) is dict:
                                key_type, val_type = typing.get_args(expected_type)
                                for k, v in value.items():
                                    if not isinstance(k, key_type):
                                        errors.append(
                                            f"参数 '{name}' 的键 '{k}' 类型错误: "
                                            f"期望 {key_type.__name__}, 实际 {type(k).__name__}"
                                        )
                                    if not isinstance(v, val_type):
                                        errors.append(
                                            f"参数 '{name}' 的值 '{v}' 类型错误: "
                                            f"期望 {val_type.__name__}, 实际 {type(v).__name__}"
                                        )
                                continue
                        
                        # 普通类型检查
                        if not isinstance(value, expected_type):
                            errors.append(
                                f"参数 '{name}' 类型错误: "
                                f"期望 {expected_type.__name__}, 实际 {type(value).__name__}"
                            )
            
            if errors:
                return False, " | ".join(errors)
            return True, None
        
        return strict_check
    def __call__(self, *args, **kwargs) -> Any:
        # 按优先级排序：先按priority值降序（数值大的优先级高），再按注册顺序升序
        sorted_overloads = sorted(self.overloads, key=lambda x: (-x[2], x[3]))
        
        # 尝试匹配函数
        for check, func, _, _ in sorted_overloads:
            try:
                if not self.is_strict:
                    # 普通模式：尝试执行函数
                    return func(*args, **kwargs)
                else:
                    # 严格模式：使用检查函数
                    is_valid, error_msg = check(args, kwargs)
                    if is_valid:
                        return func(*args, **kwargs)
                    else:
                        # 记录错误信息但继续尝试其他重载
                        last_error = error_msg
            except (TypeError, ValueError) as e:
                # 忽略参数不匹配的错误
                last_error = str(e)
                continue
        
        # 没有匹配的函数
        if self.main_func:
            try:
                return self.main_func(*args, **kwargs)
            except Exception as e:
                # 添加详细的错误信息
                if 'last_error' in locals():
                    raise TypeError(f"没有找到匹配的重载函数: {last_error}") from e
                else:
                    raise TypeError("没有找到匹配的重载函数") from e
        
        # 添加详细的错误信息
        if 'last_error' in locals():
            raise TypeError(f"没有找到匹配的重载函数: {last_error}")
        else:
            raise TypeError("没有找到匹配的重载函数")
    @classmethod
    def create(cls) -> 'OverloadManager':
        """创建新的重载管理器实例"""
        return cls()

def overload(func: Optional[Callable] = None, 
            *funcs: Callable, 
            is_strict: bool = False, 
            priority: str = 'last', 
            check: Optional[Callable] = None) -> Any:
    """
    高效的重载装饰器，支持多种模式和优先级
    priority 越大，优先级越高
    check 用于自定义参数匹配规则
    使用方式1:
        @overload
        def main_func(): ...
        
        @main_func.register
        def func1(x): ...
    
    使用方式2:
        @overload(is_strict=True, priority='first')
        def main_func(): ...
    """
    # 处理装饰器参数
    if func is None:
        # 带参数的情况：@overload(is_strict=True)
        def decorator(f: Callable) -> OverloadManager:
            manager = OverloadManager(is_strict=is_strict, global_priority=priority)
            main_priority = -10**9 if priority == 'first' else 10**9
            manager.register(f, check=check, priority=main_priority)
            return manager
        return decorator
    
    if isinstance(func, Callable) and not funcs:
        # 无参数情况：@overload
        manager = OverloadManager(is_strict=is_strict, global_priority=priority)
        main_priority = -10**9 if priority == 'first' else 10**9
        manager.register(func, check=check, priority=main_priority)
        return manager
    
    # 多函数注册：@overload(func1, func2)
    manager = OverloadManager(is_strict=is_strict, global_priority=priority)
    main_priority = -10**9 if priority == 'first' else 10**9
    manager.register(func, check=check, priority=main_priority)
    for f in funcs:
        manager.register(f, check=check)
    return manager

# 测试代码
if __name__ == "__main__":
    print("===== 方式1测试 =====")
    # 方式1: @overload + @xx.register
    @overload
    def process_data():
        return "无参数处理"
    
    @process_data.register(priority=1)
    def process_data_x(x: int):
        return f"一个参数: {x}"
    
    @process_data.register(priority=2)
    def process_data_xy(x: int, y: int):
        return f"两个参数: {x}, {y}"
    
    print(process_data())          # 无参数处理
    print(process_data(10))        # 一个参数: 10
    print(process_data(20, 30))    # 两个参数: 20, 30
    
    print("\n===== strict模式测试 =====")
    @overload(is_strict=True)
    def strict_func(a: int, b: int):
        return a + b
    
    @strict_func.register
    def strict_func_str(a: str, b: str):
        return a + b
    
    print(strict_func(1, 2))      # 3
    print(strict_func("a", "b"))  # "ab"
    try:
        strict_func(1, "b")      # 类型不匹配
    except TypeError as e:
        print(f"Expected error: {e}")
    
    print("\n===== 优先级测试 =====")
    @overload(priority='first')
    def priority_test():
        return "主函数"
    
    @priority_test.register(priority=1)
    def priority_one(arg: int):
        return f"优先级1: {arg}"
    
    @priority_test.register(priority=10)  # 更高优先级
    def priority_high(arg: str):
        return f"高优先级: {arg}"
    
    print(priority_test("hello"))  # 高优先级: hello
    print(priority_test(100))      # 优先级1: 100
    
    print("\n===== 类方法测试 =====")
    class DataProcessor:
        def __init__(self, prefix: str):
            self.prefix = prefix
            
        @overload
        def process(self):
            return f"{self.prefix}: 无参数处理"
        
        @process.register
        def _(self, x: int):
            return f"{self.prefix}: 整数处理({x})"
        
        @process.register
        def _(self, x: str):
            return f"{self.prefix}: 字符串处理({x})"
        
        @process.register
        def _(self, x: int, y: int):
            return f"{self.prefix}: 双整数处理({x}, {y})"
    
    processor = DataProcessor("处理器")
    print(processor.process())          # 处理器: 无参数处理
    print(processor.process(10))         # 处理器: 整数处理(10)
    print(processor.process("text"))     # 处理器: 字符串处理(text)
    print(processor.process(20, 30))     # 处理器: 双整数处理(20, 30)
    
    print("\n===== 生成器函数测试 =====")
    @overload
    def generate_data():
        yield from range(1, 4)
    
    @generate_data.register
    def _(count: int):
        yield from (i * 10 for i in range(1, count + 1))
    
    @generate_data.register
    def _(start: int, end: int):
        yield from (start, end, start * end)
    
    # 测试生成器调用
    print("生成器1:", list(generate_data()))         # [1, 2, 3]
    print("生成器2:", list(generate_data(3)))        # [10, 20, 30]
    print("生成器3:", list(generate_data(5, 6)))      # [5, 6, 30]
    
    print("\n===== 混合类型生成器测试 =====")
    @overload(is_strict=True)
    def generate_output(a: int):
        yield f"整数: {a}"
    
    @generate_output.register
    def _(a: str, b: str):
        yield f"字符串: {a}"
        yield f"字符串: {b}"
    
    print("混合生成器1:", list(generate_output(100)))       # ['整数: 100']
    print("混合生成器2:", list(generate_output("A", "B")))  # ['字符串: A', '字符串: B']
    
    # 新增测试：*args 和 **kwargs 参数处理
    print("\n===== *args 参数测试 =====")
    @overload
    def args_func(a, b):
        return f"固定参数: {a}, {b}"
    
    @args_func.register
    def _(a, *args):
        return f"可变位置参数: a={a}, args={args}"
    
    @args_func.register
    def _(a, b, *args):
        return f"固定+可变位置参数: a={a}, b={b}, args={args}"
    
    print(args_func(1, 2))          # 固定参数: 1, 2
    print(args_func(1))              # 可变位置参数: a=1, args=()
    print(args_func(1, 2, 3, 4))     # 固定+可变位置参数: a=1, b=2, args=(3,4)
    
    print("\n===== **kwargs 参数测试 =====")
    @overload
    def kwargs_func(a):
        return f"固定参数: {a}"
    
    @kwargs_func.register
    def _(**kwargs):
        return f"可变关键字参数: {kwargs}"
    
    @kwargs_func.register
    def _(a, **kwargs):
        return f"固定+可变关键字参数: a={a}, kwargs={kwargs}"
    
    print(kwargs_func(1))                     # 固定参数: 1
    print(kwargs_func(a=1, b=2))              # 可变关键字参数: {'a':1, 'b':2}
    print(kwargs_func(1, b=2, c=3))           # 固定+可变关键字参数: a=1, kwargs={'b':2, 'c':3}
    
    print("\n===== 混合 *args 和 **kwargs 测试 =====")
    @overload
    def mixed_func(a):
        return f"固定参数: {a}"
    
    @mixed_func.register
    def _(a, *args, **kwargs):
        return f"混合参数: a={a}, args={args}, kwargs={kwargs}"
    
    print(mixed_func(1))                     # 固定参数: 1
    print(mixed_func(1, 2, 3))               # 混合参数: a=1, args=(2,3), kwargs={}
    print(mixed_func(1, 2, b=3, c=4))        # 混合参数: a=1, args=(2,), kwargs={'b':3, 'c':4}
    
    print("\n===== 严格模式下的可变参数测试 =====")
    @overload(is_strict=True)
    def strict_args_func(a: int, *args: int):
        return (a, *args)
    
    @strict_args_func.register
    def _(a: str, b: str):
        return (a, b)
    
    print(strict_args_func(1, 2, 3))         # (1, 2, 3)
    print(strict_args_func("a", "b", "c"))    # ('a', 'b', 'c')
    try:
        strict_args_func(1, "b", 3)          # 类型不匹配
    except TypeError as e:
        print(f"Expected error: {e}")
    
    @overload(is_strict=True)
    def strict_kwargs_func(a: int, **kwargs: int):
        return {"a": a, **kwargs}
    @strict_kwargs_func.register
    @strict
    def _(a:int,**b:str):
        return {"wk":a,**b}
    
    print(strict_kwargs_func(1, b=2, c=3))    # {'a': 1, 'b': 2, 'c': 3}
    try:
        t = strict_kwargs_func(1, b="x")         # 类型不匹配
        print(t, type(t),"类型不匹配 这里应该报错; 看到打印 出错")
    except TypeError as e:
        print(f"Expected error: {e}")
    
    print("\n所有测试完成!")