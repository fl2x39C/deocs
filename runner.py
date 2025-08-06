


import time
import math
import threading
from functools import wraps, lru_cache
import inspect  
from typing import Callable, Optional, Tuple, Type, Union, Any, List, Dict,get_type_hints
from datetime import datetime
import logging
from collections import namedtuple
import re
import sys
import traceback  
from inspect import signature, Parameter
import time
from typing import  Iterator
from math import inf

__all__ = ['log_all', 'params_shell', 'params_check'
           ,'result_shell','result_check','func_shell'
           ,'func_check','run_first','run_last'
           ,'run_all','compose','rcompose']

def log_all(
    level: int = logging.INFO,
    log_args: bool = True,
    log_return: bool = True,
    log_time: bool = True,
    log_error: bool = True,
    logger: Optional[logging.Logger] = None,
    max_arg_len: int = 100,
    sensitive_args: Optional[list] = None,
    log_file: Optional[str] = None
) -> Callable:
    """
    功能全面的函数调用日志装饰器
    
    参数:
    level: 日志级别 (默认 logging.INFO)
    log_args: 是否记录参数 (默认 True)
    log_return: 是否记录返回值 (默认 True)
    log_time: 是否记录执行时间 (默认 True)
    log_error: 是否记录异常 (默认 True)
    logger: 自定义logger对象 (默认使用root logger)
    max_arg_len: 参数值最大显示长度 (默认100字符)
    sensitive_args: 敏感参数名列表 (将显示为'***')
    log_file: 日志输出文件路径 (默认不输出到文件)
    
    
    # 基本使用
    @log_all(level=logging.DEBUG)
    def add(a: int, b: int) -> int:
        return a + b
    
    # 带敏感参数
    @log_all(sensitive_args=["password"], log_file="app.log")
    def authenticate(username: str, password: str) -> bool:
        return True if username == "admin" and password == "secret" else False
    
    # 测试异常记录
    @log_all(log_error=True)
    def risky_operation():
        raise ValueError("Something went wrong")
    
    # 执行函数
    print(add(2, 3))
    print(authenticate("admin", "secret"))
    try:
        risky_operation()
    except:
        pass
    
    # 日志输出
    """
    # 配置日志记录器
    if not logger:
        logger = logging.getLogger('log_all')
        logger.setLevel(level)
        
        # 添加控制台handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        
        # 创建文件handler如果指定了文件路径
        handlers = [console_handler]
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(level)
            handlers.append(file_handler)
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        for handler in handlers:
            handler.setFormatter(formatter)
            logger.addHandler(handler)
    
    # 敏感参数处理函数
    def sanitize_args(args: tuple, kwargs: dict) -> str:
        """处理敏感参数并限制字符串长度"""
        def sanitize_value(key: str, value: Any) -> str:
            # 敏感参数处理
            if sensitive_args and key in sensitive_args:
                return "***"
            
            # 长字符串截断
            str_val = str(value)
            if len(str_val) > max_arg_len:
                return str_val[:max_arg_len] + "..."
            return str_val
        
        # 处理位置参数
        args_repr = [sanitize_value(f"arg_{i}", arg) 
                     for i, arg in enumerate(args)]
        
        # 处理关键字参数
        kwargs_repr = [f"{k}={sanitize_value(k, v)}" 
                       for k, v in kwargs.items()]
        
        return ", ".join(args_repr + kwargs_repr)
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # 记录开始时间
            start_time = time.perf_counter()
            
            try:
                result = func(*args, **kwargs)
                status = "SUCCESS"
            except Exception as e:
                status = f"FAILED ({type(e).__name__})"
                result = None
                if log_error:
                    logger.error(f"Function {func.__name__} failed with error: {str(e)}", 
                                exc_info=True)
                raise
            finally:
                # 计算执行时间
                exec_time = time.perf_counter() - start_time
                
                # 构建日志消息
                log_parts = [f"Function: {func.__name__}"]
                
                # 添加参数信息
                if log_args and (args or kwargs):
                    log_parts.append(f"Args: [{sanitize_args(args, kwargs)}]")
                
                # 添加返回信息
                if log_return and status == "SUCCESS":
                    result_repr = str(result)
                    if len(result_repr) > max_arg_len:
                        result_repr = result_repr[:max_arg_len] + "..."
                    log_parts.append(f"Return: {result_repr}")
                
                # 添加执行时间
                if log_time:
                    time_unit = "ms"
                    display_time = exec_time * 1000
                    if exec_time > 1:
                        time_unit = "s"
                        display_time = exec_time
                    log_parts.append(f"Exec: {display_time:.2f}{time_unit}")
                
                # 添加状态
                log_parts.append(f"Status: {status}")
                
                # 记录日志
                log_message = " | ".join(log_parts)
                logger.log(level, log_message)
            
            return result
        
        return wrapper
    
    return decorator

def _execute_code(code, context=None):
    """执行代码块（字符串或无参函数）"""
    if callable(code):
        # 如果是可调用对象，直接调用
        code()
    elif isinstance(code, str):
        # 如果是字符串，使用 exec 执行
        # 创建基础环境并添加上下文变量
        safe_env = {
            '__builtins__': {
                'print': print, 'len': len, 'str': str, 'int': int, 'float': float, 'bool': bool,
                'list': list, 'dict': dict, 'tuple': tuple, 'set': set
            }
        }
        # 添加上下文变量
        if context:
            safe_env.update(context)
        try:
            # 执行字符串代码
            # self = context.get('self',None)
            # exec(code, safe_env) if self is not None else exec(code,globals(),locals())
            exec(code, safe_env)
        except Exception as e:
            print(f"Error executing code: {e}")
            raise
    else:
        raise TypeError("Code must be a string or callable")

def params_shell(shell_func):
    """
    参数修改装饰器
    - shell_func: 修改函数，可以是函数或字符串表达式
    """
    def decorator(target):
        @wraps(target)
        def wrapper(*args, **kwargs):
            # 处理字符串表达式
            if isinstance(shell_func, str):
                try:
                    # 创建上下文环境
                    context = {
                        'args': args,
                        'kwargs': kwargs,
                        'self': args[0] if args and hasattr(args[0], '__dict__') else None
                    }
                    # 评估表达式
                    result = eval(shell_func, context)
                    if isinstance(result, tuple) and len(result) == 2:
                        new_args, new_kws = result
                    else:
                        new_args, new_kws = args, kwargs
                except Exception as e:
                    raise ValueError(f"Error evaluating params_shell expression: {str(e)}")
            else:
                # 直接调用函数
                new_args, new_kws = shell_func(args, kwargs)
            
            # 使用修改后的参数调用目标函数
            return target(*new_args, **new_kws)
        
        return wrapper
    
    return decorator

def params_check(check_func):
    """
    参数检查装饰器
    - check_func: 检查函数，可以是函数或字符串表达式
    """
    def decorator(target):
        # 处理函数和类
        if inspect.isclass(target):
            # 装饰类时，修改其 __init__ 方法
            original_init = target.__init__
            
            @wraps(original_init)
            def wrapped_init(self, *args, **kwargs):
                # 检查参数
                _evaluate_check_func(check_func, args, kwargs)
                original_init(self, *args, **kwargs)
            
            target.__init__ = wrapped_init
            return target
        else:
            # 装饰函数
            @wraps(target)
            def wrapper(*args, **kwargs):
                # 检查参数
                _evaluate_check_func(check_func, args, kwargs)
                return target(*args, **kwargs)
            return wrapper
    
    return decorator

def _evaluate_check_func(check_func, args, kwargs):
    """执行检查函数或表达式"""
    try:
        if callable(check_func):
            check_func(args, kwargs)
        elif isinstance(check_func, str):
            # 创建上下文环境
            context = {
                'args': args,
                'kwargs': kwargs,
                'self': args[0] if args and hasattr(args[0], '__dict__') else None
            }
            # 评估表达式
            if not eval(check_func, context):
                raise ValueError("Parameter check failed")
        else:
            if not bool(check_func):
                raise ValueError("Parameter check failed")
    except Exception as e:
        raise ValueError(f"Parameter check error: {str(e)}")

def result_shell(shell_func):
    """
    结果外壳装饰器 - 对目标函数的结果进行修饰
    - shell_func: 可以是函数或字符串表达式
    """
    def decorator(target_func):
        @wraps(target_func)
        def wrapper(*args, **kwargs):
            # 执行原函数获取结果
            result = target_func(*args, **kwargs)
            
            # 处理字符串表达式
            if isinstance(shell_func, str):
                try:
                    # 创建上下文环境
                    context = {
                        'result': result,
                        'args': args,
                        'kwargs': kwargs,
                        'self': args[0] if args and hasattr(args[0], '__dict__') else None
                    }
                    # 评估表达式
                    return eval(shell_func, context)
                except Exception as e:
                    raise ValueError(f"Error evaluating result_shell expression: {str(e)}")
            else:
                # 使用外壳函数修饰结果
                return shell_func(result)
        return wrapper
    return decorator

class ResultError(Exception):
    pass

def result_check(check_func, describe):
    """_summary_

    Args:
        check_func (_type_): _description_
        describe (_type_): _description_
        
    @result_check(lambda x: x > 0, "Result must be positive")
    def test_func(x):
        return x * 2

    try:
        print(test_func(5))  # 输出: 10
        test_func(-1)       # 触发错误
    except ResultError as e:
        print(e)  # 输出: Result must be positive

    @result_check("self.value > 0", "Instance value must be positive")
    class MyClass:
        def __init__(self, value):
            self.value = value

    try:
        obj = MyClass(10)  # 正常创建
        print("MyClass created with value 10")
        obj = MyClass(-5)  # 触发错误
    except ResultError as e:
        print(e)  # 输出: Instance value must be positive
        
    """
    def decorator(target):
        # 在装饰器内部定义 _evaluate_check，使其能访问 target
        def _evaluate_check(obj, *args, **kwargs):
            """执行检查并处理结果"""
            try:
                if callable(check_func):
                    success = check_func(obj)
                elif isinstance(check_func, str):
                    # 创建包含所有变量和self的上下文
                    context = {
                        'self': args[0] if args and hasattr(args[0], '__dict__') else None,
                        'result': obj,
                        'args': args,
                        'kwargs': kwargs
                    }
                    success = eval(check_func, context)
                else:
                    success = bool(check_func)
            except Exception as e:
                # 移除 last_result_error 相关代码
                raise ResultError(f"Check function failed: {str(e)}") from e
            
            if not success:
                # 移除 last_result_error 相关代码
                raise ResultError(describe)
        
        if isinstance(target, type):  # 装饰类
            class WrappedClass(target):
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, **kwargs)
                    # 调用检查函数，传入实例
                    _evaluate_check(self, *args, **kwargs)
            return WrappedClass
        
        else:  # 装饰函数
            def wrapper(*args, **kwargs):
                result = target(*args, **kwargs)
                # 调用检查函数，传入结果
                _evaluate_check(result, *args, **kwargs)
                return result
            return wrapper
    
    return decorator

def func_shell(shell_func):
    """
    函数外壳装饰器 - 对目标函数本身进行修饰
    - shell_func: 单参函数，接收目标函数本身，返回新的函数
    """
    def decorator(target_func):
        # 使用外壳函数包装目标函数
        wrapped_func = shell_func(target_func)
        # 保留元信息
        @wraps(target_func)
        def wrapper(*args, **kwargs):
            return wrapped_func(*args, **kwargs)
        
        return wrapper
    return decorator
def run_first(code):
    """
    在目标函数执行前执行代码
    - code: 字符串（将被 exec 执行）或无参函数
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # # 获取self的逻辑
            # self_obj = None
            # # 1. 优先从位置参数获取
            # if args and hasattr(args[0], '__dict__'):
            #     self_obj = args[0]
            # # 2. 从调用栈查找（处理无参函数场景）
            # else:
            #     try:
            #         stack = inspect.stack()
            #         # 遍历调用栈查找可能的类实例
            #         for frame_info in stack[2:]:  # 跳过当前wrapper和装饰器帧
            #             frame = frame_info.frame
            #             self_candidate = frame.f_locals.get('self')
            #             if self_candidate and hasattr(self_candidate, '__dict__'):
            #                 # 验证该实例是否包含当前函数
            #                 if func.__name__ in dir(self_candidate):
            #                     self_obj = self_candidate
            #                     break
            #     except Exception as e:
            #         print(f"获取self失败: {e}")

            # # 创建执行上下文
            # context = {
            #     'args': args,
            #     'kwargs': kwargs,
            #     'self': self_obj
            # }
            # # 执行前置代码并传递上下文
            # _execute_code(code, context)
            if callable(code):
                code()
            elif isinstance(code,str):
                exec(code,globals(),locals())
            return func(*args, **kwargs)
        return wrapper
    return decorator

def run_last(code):
    """
    在目标函数执行后执行代码
    - code: 字符串（将被 exec 执行）或无参函数
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            # 获取self的逻辑
            self_obj = None
            # 1. 优先从位置参数获取
            if args and hasattr(args[0], '__dict__'):
                self_obj = args[0]
            # 2. 从调用栈查找（处理无参函数场景）
            else:
                try:
                    stack = inspect.stack()
                    # 遍历调用栈查找可能的类实例
                    for frame_info in stack[2:]:  # 跳过当前wrapper和装饰器帧
                        frame = frame_info.frame
                        self_candidate = frame.f_locals.get('self')
                        if self_candidate and hasattr(self_candidate, '__dict__'):
                            # 验证该实例是否包含当前函数
                            if func.__name__ in dir(self_candidate):
                                self_obj = self_candidate
                                break
                except Exception as e:
                    print(f"获取self失败: {e}")

            # 创建执行上下文
            context = {
                'args': args,
                'kwargs': kwargs,
                'result': result,
                'self': self_obj
            }
            # 执行后置代码并传递上下文
            _execute_code(code, context)
            # if callable(code):
            #     code()
            # elif isinstance(code,str):
            #     exec(code,globals(),locals())
            return result
        return wrapper
    return decorator

def run_code(first=None, last=None):
    """
    在目标函数执行前后执行代码
    - first: 前置代码（字符串或无参函数）
    - last: 后置代码（字符串或无参函数）
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 获取self的逻辑
            self_obj = None
            # 1. 优先从位置参数获取
            if args and hasattr(args[0], '__dict__'):
                self_obj = args[0]
            # 2. 从调用栈查找（处理无参函数场景）
            else:
                try:
                    stack = inspect.stack()
                    # 遍历调用栈查找可能的类实例
                    for frame_info in stack[2:]:  # 跳过当前wrapper和装饰器帧
                        frame = frame_info.frame
                        self_candidate = frame.f_locals.get('self')
                        if self_candidate and hasattr(self_candidate, '__dict__'):
                            # 验证该实例是否包含当前函数
                            if func.__name__ in dir(self_candidate):
                                self_obj = self_candidate
                                break
                except Exception as e:
                    print(f"获取self失败: {e}")

            # 创建执行上下文
            context = {
                'args': args,
                'kwargs': kwargs,
                'result': None,
                'self': self_obj
            }
            # 执行前置代码
            if first:
                _execute_code(first,context)
            
            result = func(*args, **kwargs)
            context['result'] = result
            # 执行后置代码
            if last:
                _execute_code(last,context)
            
            return result
        return wrapper
    return decorator


def run_all(
    fun_deco: Optional[Callable] = None,
    params_modify_func: Optional[Callable] = None,
    params_check_func: Optional[Callable] = None,
    code_first: Union[str, Callable, None] = None,
    code_last: Union[str, Callable, None] = None,
    result_func: Optional[Callable] = None,
    result_check_info: Optional[Tuple[Any, str]] = None,
    log_all_info: Union[bool, Dict, None] = None
) -> Callable:
    """
    综合性装饰器，整合多种功能：
    1. 函数修饰 (func_shell)
    2. 参数修改 (params_shell)
    3. 参数检查 (params_check)
    4. 前置代码执行 (run_first)
    5. 后置代码执行 (run_last)
    6. 结果修饰 (result_shell)
    7. 结果检查 (result_check)
    8. 日志记录 (log_all)
    
    参数:
        fun_deco: 函数外壳装饰器
        params_modify_func: 参数修改函数
        params_check_func: 参数检查函数
        code_first: 前置代码 (字符串或可调用对象)
        code_last: 后置代码 (字符串或可调用对象)
        result_func: 结果修饰函数
        result_check_info: 结果检查信息 (check_func, describe)
        log_all_info: 日志配置 (True 使用默认配置 或 字典配置)
        
    执行顺序:
        1. 函数外壳 (func_shell)
        2. 参数修改 (params_shell)
        3. 参数检查 (params_check)
        4. 前置代码 (run_first)
        5. 后置代码 (run_last)
        6. 结果修饰 (result_shell)
        7. 结果检查 (result_check)
        8. 日志记录 (log_all)
    """
    # 构建装饰器列表 (按执行顺序)
    decorators = []
    
    # 1. 函数外壳装饰器
    if fun_deco is not None:
        decorators.append(func_shell(fun_deco))
    
    # 2. 参数修改装饰器
    if params_modify_func is not None:
        decorators.append(params_shell(params_modify_func))
    
    # 3. 参数检查装饰器
    if params_check_func is not None:
        decorators.append(params_check(params_check_func))
    
    # 4. 前置代码装饰器
    if code_first is not None:
        decorators.append(run_first(code_first))
    
    # 5. 后置代码装饰器
    if code_last is not None:
        decorators.append(run_last(code_last))
    
    # 6. 结果修饰装饰器
    if result_func is not None:
        decorators.append(result_shell(result_func))
    
    # 7. 结果检查装饰器
    if result_check_info is not None:
        check_func, describe = result_check_info
        decorators.append(result_check(check_func, describe))
    
    # 8. 日志记录装饰器
    if log_all_info is not None:
        if isinstance(log_all_info, dict):
            decorators.append(log_all(**log_all_info))
        else:
            decorators.append(log_all())
    
    # 使用 compose 组合所有装饰器
    return compose(*decorators, ignore_none=True)
class ComposeError(Exception):
    """Composition operation error"""
    pass

def compose(
    *decorators: Callable,
    ignore_none: bool = True,
    conditional: Optional[Callable] = None,
    debug: bool = False
) -> Callable:
    """
    从左向右组合多个装饰器（函数式组合顺序）
    
    参数:
    decorators: 要组合的装饰器列表
    ignore_none: 是否忽略None值装饰器 (默认True)
    conditional: 条件函数，接受装饰器并返回是否应用的布尔值
    debug: 是否启用调试模式，打印应用过程
    
    示例:
    @compose(log_all(), memoize, validate_args)
    def my_func(x):
        return x * 2
    
        
    # ============= 使用示例 =============
    import time
    from functools import lru_cache

    # 1. 基本组合示例
    @compose(
        debug_decorator,
        lru_cache(maxsize=128),
        retry(tries=3, exceptions=(ConnectionError,))
    )
    def fetch_data(url: str) -> Any:
        # 模拟数据获取函数
        print(f"Fetching data from {url}")
        if "fail" in url:
            raise ConnectionError("Connection failed")
        return {"data": "example", "url": url}

    # 2. 条件组合示例
    def is_performance_decorator(dec: Callable) -> bool:
        # # 判断是否是性能相关装饰器
        return hasattr(dec, '__name__') and 'cache' in dec.__name__.lower()

    @compose(
        debug_decorator,  # 会被包含
        lru_cache(maxsize=128),  # 会被包含
        retry(tries=3),  # 不会被包含
        conditional=is_performance_decorator
    )
    def calculate(x: int) -> int:
        # # 计算函数
        print(f"Calculating for {x}")
        return x * x

    # 3. 带参数验证的组合
    @rcompose(
        validate_args({
            'x': {'type': int, 'min': 1, 'max': 100},
            'y': {'type': str, 'validator': lambda s: len(s) > 0}
        }),
        debug_decorator
    )
    def process_values(x: int, y: str) -> str:
        # # 处理数值和字符串
        return f"Processed: {x} * {y} = {y * x}"

    # 4. 复杂组合示例
    def log_exec_time(func: Callable) -> Callable:
        # # 执行时间记录装饰器
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            result = func(*args, **kwargs)
            end = time.perf_counter()
            print(f"{func.__name__} executed in {end-start:.4f} seconds")
            return result
        return wrapper

    @compose(
        log_exec_time,
        retry(tries=2, delay=0.5),
        validate_args({'n': {'type': int, 'min': 1}}),
        debug=True  # 启用调试模式
    )
    def factorial(n: int) -> int:
        # 计算阶乘
        if n == 1:
            return 1
        return n * factorial(n - 1)

    if __name__ == "__main__":
        print("===== Basic Composition Test =====")
        try:
            print(fetch_data("https://fail.example.com"))
        except ConnectionError as e:
            print(f"Final error: {str(e)}")
        
        print("\n===== Conditional Composition Test =====")
        print(calculate(5))  # 应看到缓存效果
        
        print("\n===== Validation Test =====")
        try:
            print(process_values(0, "test"))  # 应触发验证错误
        except ValueError as e:
            print(f"Validation failed: {str(e)}")
        
        print("\n===== Complex Composition Test =====")
        print(factorial(5))
    """
    valid_decorators = []
    
    # 过滤和处理装饰器
    for i, dec in enumerate(decorators):
        if dec is None and ignore_none:
            continue
            
        if not callable(dec):
            raise ComposeError(f"Decorator at position {i} is not callable: {type(dec)}")
            
        if conditional and not conditional(dec):
            if debug:
                print(f"Skipping decorator {dec.__name__} due to condition")
            continue
                
        valid_decorators.append(dec)
    
    if not valid_decorators:
        # 如果没有有效装饰器，返回恒等函数
        return lambda func: func
    
    def composed_decorator(func: Callable) -> Callable:
        # 从右向左应用装饰器（实际执行顺序）
        result = func
        for dec in reversed(valid_decorators):
            if debug:
                print(f"Applying decorator: {getattr(dec, '__name__', type(dec).__name__)}")
            result = dec(result)
        return result
    
    return composed_decorator

def rcompose(
    *decorators: Callable,
    ignore_none: bool = True,
    conditional: Optional[Callable] = None,
    debug: bool = False
) -> Callable:
    """
    从右向左组合多个装饰器（反向函数式组合顺序）
    
    参数:
    decorators: 要组合的装饰器列表
    ignore_none: 是否忽略None值装饰器 (默认True)
    conditional: 条件函数，接受装饰器并返回是否应用的布尔值
    debug: 是否启用调试模式，打印应用过程
    
    示例:
    @rcompose(validate_args, memoize, log_all())
    def my_func(x):
        return x * 2
        
    more doc in compose()
    

    """
    # 直接反转参数顺序调用compose
    return compose(*reversed(decorators), 
                   ignore_none=ignore_none,
                   conditional=conditional,
                   debug=debug)
