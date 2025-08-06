import time
from typing import Any, Callable, Iterator, Union, Optional, TypeVar
from functools import wraps
import inspect
import random

__all__ = ["repeat"]

# 定义可调用类型变量
F = TypeVar('F', bound=Callable[..., Any])

def repeat(
    cnt: Union[int, Callable[[], bool], Any] = 1, 
    delay: float = 0
) -> Callable[[F], F]:
    """
    重复执行被装饰函数的装饰器工厂
    
    此装饰器创建一个生成器，可多次执行被装饰函数，每次执行后可选延迟。
    支持多种调用模式：
    1. 固定次数重复
    2. 无限重复（直到手动中断）
    3. 条件重复（通过可调用对象控制）
    
    参数:
        cnt: 重复次数或停止条件
            - int: 
                >0 - 执行指定次数 
                <0 - 无限循环
                =0 - 不执行
            - 可调用对象: 每次迭代前调用，返回False时停止
            - 其他类型: 转换为布尔值，True时执行一次，False时不执行
        delay: 每次调用后的延迟时间（秒），0表示无延迟
    
    返回:
        装饰器函数：返回生成器迭代器，每次迭代产生函数返回值
    
    注意事项:
        1. 不适用于生成器函数（yield函数）
        2. 装饰类方法时自动传递self/cls
        3. 参数验证基于函数签名
        4. 延迟使用time.sleep()实现
    
    示例:
        >>> # 示例1: 固定次数调用
        >>> @repeat(cnt=3, delay=0.5)
        ... def greet(name):
        ...     return f"Hello, {name}!"
        ...
        >>> for result in greet("Alice"):
        ...     print(result)
        Hello, Alice!
        Hello, Alice!
        Hello, Alice!
        
        >>> # 示例2: 条件调用
        >>> counter = 0
        >>> def should_continue():
        ...     global counter
        ...     counter += 1
        ...     return counter <= 3
        ...
        >>> @repeat(cnt=should_continue)
        ... def count_up():
        ...     return counter
        ...
        >>> list(count_up())
        [1, 2, 3]
        
        >>> # 示例3: 类方法装饰
        >>> class Greeter:
        ...     @repeat(cnt=2, delay=0.1)
        ...     def greet(self, name):
        ...         return f"Hi, {name} from class!"
        ...
        >>> g = Greeter()
        >>> [res for res in g.greet("Bob")]
        ['Hi, Bob from class!', 'Hi, Bob from class!']
        
        >>> # 示例4: 无限循环（需手动中断）
        >>> @repeat(cnt=-1, delay=1)
        ... def infinite():
        ...     return "Looping forever"
        ...
        >>> # 实际使用时需要手动中断迭代
        >>> # 测试中取前2个结果
        >>> gen = infinite()
        >>> next(gen), next(gen)
        ('Looping forever', 'Looping forever')
        
        >>> # 示例5: 单次执行
        >>> @repeat(cnt=False)  # 布尔值False不执行
        ... def no_run():
        ...     print("This won't run")
        ...
        >>> list(no_run())
        []
    """
    def decorator(func: F) -> F:
        # 分析函数签名
        sig = inspect.signature(func)
        required_params = []
        has_var_positional = False
        has_var_keyword = False
        
        # 分析函数参数特性
        for param in sig.parameters.values():
            if param.default is param.empty and param.kind not in (
                param.VAR_POSITIONAL, param.VAR_KEYWORD
            ):
                required_params.append(param.name)
                
            if param.kind == param.VAR_POSITIONAL:
                has_var_positional = True
            if param.kind == param.VAR_KEYWORD:
                has_var_keyword = True
                
        min_args_count = len(required_params)
        
        @wraps(func)
        def wrapper(*args, **kwargs) -> Iterator[Any]:
            # 参数验证
            if len(args) + len(kwargs) < min_args_count:
                raise TypeError(f"缺少必选参数: 需要至少 {min_args_count} 个参数")
                
            if not has_var_positional and len(args) > len(sig.parameters):
                raise TypeError(f"位置参数过多: 最多接受 {len(sig.parameters)} 个位置参数")
                
            if not has_var_keyword:
                valid_params = set(sig.parameters.keys())
                extra_kwargs = set(kwargs.keys()) - valid_params
                if extra_kwargs:
                    raise TypeError(f"无效关键字参数: {', '.join(extra_kwargs)}")
            
            # 执行逻辑
            # 情况1: cnt是可调用对象（条件函数）
            if callable(cnt):
                while True:
                    if not cnt():  # 条件为False时停止
                        break
                    result = func(*args, **kwargs)
                    yield result
                    if delay > 0:
                        time.sleep(delay)
            
            # 情况2: cnt是整数
            elif isinstance(cnt, int):
                # 负数表示无限循环
                if cnt < 0:
                    while True:
                        result = func(*args, **kwargs)
                        yield result
                        if delay > 0:
                            time.sleep(delay)
                # 零表示不执行
                elif cnt == 0:
                    return
                # 正数执行指定次数
                else:
                    for i in range(cnt):
                        result = func(*args, **kwargs)
                        yield result
                        # 最后一次不延迟
                        if i < cnt - 1 and delay > 0:
                            time.sleep(delay)
            
            # 情况3: 其他类型（转换为布尔值判断）
            else:
                if bool(cnt):
                    yield func(*args, **kwargs)
        
        return wrapper  # type: ignore
    return decorator


if __name__ == '__main__':
    import sys
    
    # 测试1: 基本功能测试
    @repeat(cnt=3, delay=0.5)
    def hello(name: str) -> str:
        """返回个性化问候语"""
        w = random.choice(["Alice", "Bob", "Charlie"])
        return f"Hello, {name}! Also say hi to {w}"
    
    print("\n=== 测试1: 基本功能 ===")
    for i, result in enumerate(hello("World")):
        print(f"调用 {i+1}: {result}")
    
    # 测试2: 类方法
    class Greeter:
        @repeat(cnt=2, delay=0.3)
        def greet(self, name: str) -> str:
            """类方法问候"""
            return f"Class says hi to {name}"
    
    print("\n=== 测试2: 类方法 ===")
    g = Greeter()
    for i, res in enumerate(g.greet("Python")):
        print(f"类方法调用 {i+1}: {res}")
    
    # 测试3: 条件控制
    print("\n=== 测试3: 条件控制 ===")
    counter = 0
    def should_continue() -> bool:
        """条件函数：最多执行3次"""
        global counter
        counter += 1
        return counter <= 3
    
    @repeat(cnt=should_continue)
    def conditional() -> int:
        """条件执行函数"""
        return counter
    
    print("条件执行结果:", list(conditional()))
    
    # 测试4: 边界情况
    print("\n=== 测试4: 边界情况 ===")
    
    # 测试4.1: 零次执行
    @repeat(cnt=0)
    def never_run() -> str:
        return "这不应该出现"
    
    print("零次执行结果:", list(never_run()))  # 预期空列表
    
    # 测试4.2: 单次执行
    @repeat(cnt=True)
    def run_once() -> int:
        return 42
    
    print("单次执行结果:", list(run_once()))  # 预期[42]
    
    # 测试4.3: 无限执行（测试中取2次）
    @repeat(cnt=-1, delay=0.1)
    def infinite() -> int:
        return random.randint(1, 100)
    
    print("无限执行(取样):", [next(infinite()) for _ in range(2)])
    
    # 测试5: 错误处理
    print("\n=== 测试5: 错误处理 ===")
    
    # 测试5.1: 缺少必选参数
    @repeat()
    def requires_arg(x):
        return x
    
    try:
        print("缺少参数测试...")
        list(requires_arg())
    except TypeError as e:
        print(f"预期错误: {e}")
    
    # 测试5.2: 多余参数
    @repeat()
    def simple_func():
        return True
    
    try:
        print("多余参数测试...")
        list(simple_func(1))
    except TypeError as e:
        print(f"预期错误: {e}")
    
    print("\n所有测试完成!")
    sys.exit(0)