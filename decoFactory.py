




# 在文件顶部添加
__all__ = [
    # 装饰器类
    'OverloadManager', 'Curried', 
    # 核心装饰器
    'overload', 'repeat', 'curry', 'static_vars', 'decorator', 'once', 'iterable',
    'ignore_errs', 'first_check', 'print_exceptions', 'log_all', 'retry',
    # 参数处理
    'params_shell', 'params_check',
    # 结果处理
    'result_shell', 'ResultError', 'result_check',
    # 执行控制
    'run_first', 'run_last', 'run_code',
    # 组合工具
    'run_all', 'compose', 'rcompose', 'deco_all',
    # 辅助工具
    'analyze_parameters', 'analyze_parameters_'
]

__decos__ = {
    # 函数重载
    'overload': ['overload', 'OverloadManager'],
    # 柯里化
    'curry': ['curry', 'Curried'],
    # 控制流
    'control': ['repeat', 'once', 'iterable', 'first_check', 'run_first', 'run_last', 'run_code'],
    # 错误处理
    'error': ['ignore_errs', 'print_exceptions', 'retry'],
    # 日志记录
    'log': ['log_all'],
    # 参数处理
    'params': ['params_shell', 'params_check'],
    # 结果处理
    'result': ['result_shell', 'result_check'],
    # 组合工具
    'compose': ['compose', 'rcompose', 'run_all', 'deco_all'],
    # 辅助工具
    'utils': ['static_vars', 'analyze_parameters', 'analyze_parameters_', 'decorator']
}

__doc__ = """
decoFactory - 强大的Python装饰器工厂

本模块提供了一系列功能丰富的装饰器，用于增强Python函数的功能，包括：
1. 函数重载（overload）
2. 柯里化（curry）
3. 控制流（重复执行、条件执行等）
4. 错误处理和日志记录
5. 参数和结果处理
6. 装饰器组合工具

主要功能分类：
- 函数重载：支持多种匹配模式和优先级控制
- 柯里化：支持严格类型检查的柯里化函数
- 控制流：重复执行、首次执行逻辑、条件执行等
- 错误处理：忽略指定错误、重试机制、异常日志
- 日志记录：详细的函数调用日志
- 参数处理：参数修改和验证
- 结果处理：结果修改和验证
- 组合工具：灵活组合多个装饰器

使用示例见模块底部的测试代码
"""



# import time
# import math
# import threading
# from functools import wraps, lru_cache
# import inspect  
# from typing import Callable, Optional, Tuple, Type, Union, Any, List, Dict,get_type_hints
# from datetime import datetime
# import logging
# from collections import namedtuple
# import re
# import sys
# import traceback  
# from inspect import signature, Parameter
# import time
# from typing import  Iterator
# from math import inf

import inspect
import types
from functools import wraps




from overload import overload, OverloadManager, strict
from once import once
from iterable import iterable
from first_check import first_check, first_init
from repeat import repeat
from curry import curry, Curried
from memorize import memorize
from retry import retry
from runner import run_first, run_last, run_code,result_check,result_shell,run_all,compose,rcompose,params_check,params_shell
from delay_curry import delay_curry,DelayCurried,is_lazy,lazy
from stuff import stuff,Stuff
from calltype import CallableType,get_callable_type,create_fake

from errs import print_exceptions, ignore_errs
from utils import static_vars, analyze_parameters, analyze_parameters_,validate_args,log_exec_time,swap2,counting_sort

def decorator(wrapper):
    """增强版装饰器，保留完整函数签名
    
        example:
        
            
        @decorator
        def validate_input(call):
            def validation_wrapper(*args, **kwargs):
                for arg in args:
                    if not isinstance(arg, int):
                        raise TypeError("所有参数必须是整数")
                return call(*args, **kwargs)
            return validation_wrapper

        @validate_input
        def multiply(a: int, b: int) -> int:
            return a * b

        # 检查签名保留情况
        print(inspect.signature(multiply))  # (a: int, b: int) -> int
        print(multiply(2, 3))  # 6
        print(multiply(2.5, 3))  # TypeError: 所有参数必须是整数
    
    """
    def actual_decorator(func):
        # 使用 functools.wraps 保留基础元信息
        @wraps(func)
        def inner_wrapper(*args, **kwargs):
            return wrapper(func)(*args, **kwargs)
        # 保留原始函数的签名
        inner_wrapper.__signature__ = inspect.signature(func)
        return inner_wrapper
    return actual_decorator



def deco_all(*decos, **deco_kws):
    """
    万能装饰器组合器，可以组合多个装饰器并为每个装饰器指定参数
    
    参数:
        decos: 要应用的装饰器列表
        deco_kws: 装饰器参数，格式为 {装饰器名}__args 和 {装饰器名}__kws
        
    使用示例:
        # 基本使用
        @deco_all(log_all, once)
        def my_function():
            ...
            
        # 为装饰器指定参数
        @deco_all(
            log_all, 
            once,
            log_all__kws={'level': logging.DEBUG, 'log_file': 'app.log'},
            once__kws={'interval_time': 10}
        )
        def my_function():
            ...
            
        # 使用装饰器工厂
        @deco_all(
            retry, 
            retry__kws={'tries': 5, 'delay': 0.5}
        )
        def my_function():
            ...
    """
    # 用于存储配置好的装饰器
    configured_decorators = []
    
    # 处理每个装饰器
    for deco in decos:
        # 获取装饰器的名称（用于参数匹配）
        deco_name = deco.__name__
        
        # 获取该装饰器的位置参数和关键字参数
        args = deco_kws.get(f"{deco_name}__args", ())
        kws = deco_kws.get(f"{deco_name}__kws", {})
        
        # 如果提供了参数，则调用装饰器工厂
        if args or kws:
            configured_deco = deco(*args, **kws)
        else:
            # 如果没有参数，直接使用装饰器
            configured_deco = deco
        
        configured_decorators.append(configured_deco)
    
    # 使用compose组合所有装饰器
    return compose(*configured_decorators)



if __name__ == '__main__':
    print(dir(retry))
#     import math
#     import time
#     import random
#     import logging
#     from datetime import datetime
    
#     print("="*50)
#     print("开始测试 decoFactory 模块")
#     print("="*50)
    
#     # 配置日志
#     logging.basicConfig(level=logging.INFO)
    
#     # 1. 测试 overload
#     print("\n=== 测试 overload ===")
    
#     @overload
#     def process_data():
#         return "无参数处理"
    
#     @process_data.register(priority=1)
#     def process_data_x(x: int):
#         return f"一个参数: {x}"
    
#     @process_data.register(priority=2)
#     def process_data_xy(x: int, y: int):
#         return f"两个参数: {x}, {y}"
    
#     print(process_data())          # 无参数处理
#     print(process_data(10))        # 一个参数: 10
#     print(process_data(20, 30))    # 两个参数: 20, 30
    
#     # 2. 测试 repeat
#     print("\n=== 测试 repeat ===")
    
#     @repeat(cnt=3, delay=0.1)
#     def greet(name):
#         return f"Hello, {name}!"
    
#     for msg in greet("Alice"):
#         print(msg)
    
#     # 3. 测试 curry
#     print("\n=== 测试 curry ===")
    
#     @curry
#     def add(a, b, c):
#         return a + b + c
    
#     add5 = add(5)
#     add53 = add5(3)
#     print(add53(2))  # 10
    
#     # 4. 测试 static_vars
#     print("\n=== 测试 static_vars ===")
    
#     @static_vars(counter=0)
#     def count_calls():
#         count_calls.counter += 1
#         return count_calls.counter
    
#     print(count_calls())  # 1
#     print(count_calls())  # 2
    
#     # 5. 测试 once
#     print("\n=== 测试 once ===")
    
#     @once(interval_time=2)
#     def get_timestamp():
#         return datetime.now()
    
#     print("第一次:", get_timestamp())
#     print("第二次(立即):", get_timestamp())
#     time.sleep(2.5)
#     print("第三次(2.5秒后):", get_timestamp())
    
#     # 6. 测试 iterable
#     print("\n=== 测试 iterable ===")
    
#     @iterable(predicate=lambda x: x == 0)
#     def random_until_zero():
#         return random.randint(-1, 1)
    
#     print("随机直到0:", list(random_until_zero))
    
#     # 7. 测试 ignore_errs
#     print("\n=== 测试 ignore_errs ===")
    
#     @ignore_errs([ZeroDivisionError, ValueError,TypeError], defaults=["除零错误", "数值错误","类型错误"])
#     def safe_divide(a, b):
#         return a / b
    
#     print(safe_divide(10, 2))  # 5.0
#     print(safe_divide(10, 0))  # 除零错误
#     print(safe_divide("a", 2)) # 数值错误
    
#     # 8. 测试 first_check
#     print("\n=== 测试 first_check ===")
    
#     def init_db():
#         print("✅ 首次执行：建立数据库连接")
    
#     def close_db():
#         print("✅ 首次执行：提交事务并关闭连接")
    
#     @first_check(code_before=init_db, code_after=close_db)
#     def db_operation(user_id):
#         print(f"📊 处理用户 {user_id} 的数据...")
    
#     db_operation(1)
#     db_operation(2)
    
#     # 9. 测试 print_exceptions
#     print("\n=== 测试 print_exceptions ===")
    
#     @print_exceptions(filepath=None, last_error_only=False)
#     def risky_operation():
#         return 1 / 0
    
#     try:
#         risky_operation()
#     except:
#         print("捕获到异常")
    
#     # 10. 测试 log_all
#     print("\n=== 测试 log_all ===")
    
#     @log_all(level=logging.INFO, sensitive_args=["password"])
#     def login(username, password):
#         print(f"用户 {username} 登录中...")
#         return {"status": "success", "user": username}
    
#     login("admin", "secret123")
    
#     # 11. 测试 retry
#     print("\n=== 测试 retry ===")
    
#     @retry(tries=3, delay=0.5)
#     def unreliable_request():
#         if random.random() < 0.7:
#             raise ConnectionError("网络连接失败")
#         return "请求成功"
    
#     print(unreliable_request())
    
#     # 12. 测试 params_shell 和 params_check
#     print("\n=== 测试 params_shell 和 params_check ===")
    
#     @params_shell(lambda args, kwargs: ([x*2 for x in args], kwargs))
#     @params_check(lambda args, kwargs: all(isinstance(x, int) for x in args))
#     def double_sum(a, b):
#         return a + b
    
#     print(double_sum(2, 3))  # (2*2 + 3*2) = 10
    
#     # 13. 测试 result_shell 和 result_check
#     print("\n=== 测试 result_shell 和 result_check ===")
    
#     @result_shell(lambda res: res * 2)
#     @result_check(lambda x: x > 0, "结果必须为正数")
#     def calculate(x):
#         return x * 10
    
#     print(calculate(5))  # 100 (5*10*2)
    
#     # 14. 测试 run_first 和 run_last
#     print("\n=== 测试 run_first 和 run_last ===")
    
#     def pre_task():
#         print("前置任务执行")
    
#     def post_task():
#         print("后置任务执行")
    
#     @run_first(pre_task)
#     @run_last(post_task)
#     def main_task():
#         print("主任务执行")
    
#     main_task()
    
#     # 15. 测试 compose 和 rcompose
#     print("\n=== 测试 compose 和 rcompose ===")
    
#     def double(func):
#         def wrapper(*args, **kwargs):
#             return func(*args, **kwargs) * 2
#         return wrapper
    
#     def square(func):
#         def wrapper(*args, **kwargs):
#             result = func(*args, **kwargs)
#             return result * result
#         return wrapper
    
#     @compose(double, square)
#     def add_compose(a, b):
#         return a + b
    
#     @rcompose(double, square)
#     def add_rcompose(a, b):
#         return a + b
    
#     print("compose(2+3):", add_compose(2, 3))  # ((2+3)^2)*2 = 50
#     print("rcompose(2+3):", add_rcompose(2, 3))  # (2+3)*2)^2 = 100
    
#     # 16. 测试 run_all
#     print("\n=== 测试 run_all ===")
    
#     def log_args(args, kwargs):
#         print(f"参数: args={args}, kwargs={kwargs}")
    
#     def log_result(result):
#         print(f"结果: {result}")
#         return result
    
#     @run_all(
#         params_modify_func=lambda args, kwargs: (args, {**kwargs, "extra": True}),
#         params_check_func=lambda args, kwargs: all(x > 0 for x in args),
#         code_first="print('开始执行')",
#         code_last="print('执行结束')",
#         result_func=log_result
#     )
#     def complex_operation(a, b):
#         return a * b
    
#     print(complex_operation(3, 4))
    
#     # 17. 测试 deco_all
#     print("\n=== 测试 deco_all ===")
    
#     @deco_all(
#         log_all,
#         retry,
#         log_all__kws={'level': logging.DEBUG},
#         retry__kws={'tries': 3, 'delay': 0.3}
#     )
#     def combined_operation(x):
#         if random.random() < 0.5:
#             raise ValueError("随机错误")
#         return x ** 2
    
#     print(combined_operation(4))
    
#     # 18. 测试 analyze_parameters
#     print("\n=== 测试 analyze_parameters ===")
    
#     def sample_func(a, b=1, *args, **kwargs):
#         pass
    
#     info = analyze_parameters(sample_func)
#     print(f"参数分析: required={info.required}, optional={info.optional}")
    
#     print("\n" + "="*50)
#     print("所有装饰器测试完成")
#     print("="*50)


