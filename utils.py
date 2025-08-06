
from typing import Any, List, Optional, Union, Tuple, Dict, Callable
import re
from collections import namedtuple
import inspect
import time
from functools import wraps
from functools import wraps,update_wrapper


def static_vars(**kwargs):
    def decorate(func):
        for k, v in kwargs.items():
            setattr(func, k, v)
        return func
    return decorate

# 定义返回的命名元组结构
ParamInfo = namedtuple('ParamInfo', [
    'required',          # 必选参数名列表
    'optional',          # 可选参数名列表
    'has_var_args',      # 是否有 *args
    'has_var_kwargs',    # 是否有 **kwargs
    'required_count',    # 必选参数个数
    'optional_count'     # 可选参数个数
])

def analyze_parameters(
    obj: Any,
    need: Optional[Union[str, int, List[Union[str, int]]]] = None
) -> Union[ParamInfo, type]:
    """
    分析对象参数结构
    
    参数:
        obj: 要分析的对象 (函数, 类, 实例等)
        need: 过滤条件，可以是:
            - None: 返回所有参数
            - 字符串: 用空格/逗号/分号分隔的参数名或索引
            - 整数: 单个参数索引 (0-6 或 -1--7)
            - 列表: 参数名或索引的组合
    
    返回:
        ParamInfo 命名元组 或 对象类型 (当不可调用时)
    """
    # 处理不可调用对象
    if not callable(obj):
        # return [str(type(obj))]
        raise TypeError("obj must be callable")
    
    # 获取函数签名
    if inspect.isclass(obj):
        # 类对象：分析 __init__ 方法
        func = obj.__init__
        skip_self = True
    else:
        # 函数或方法
        func = obj
        skip_self = inspect.ismethod(func) and func.__self__ is not None
    
    try:
        sig = inspect.signature(func)
    except ValueError:
        # 处理内置函数等无法获取签名的对象
        return ParamInfo([], [], False, False, 0, 0)
    
    # 解析参数
    parameters = list(sig.parameters.values())
    
    # 跳过 self/cls 参数
    if skip_self and parameters:
        parameters = parameters[1:]
    
    # 分类参数
    required = []       # 必选参数
    optional = []       # 可选参数
    has_var_args = False   # 是否有 *args
    has_var_kwargs = False  # 是否有 **kwargs
    
    for param in parameters:
        if param.kind == param.VAR_POSITIONAL:
            has_var_args = True
        elif param.kind == param.VAR_KEYWORD:
            has_var_kwargs = True
        elif param.default == param.empty:
            required.append(param.name)
        else:
            optional.append(param.name)
    
    # 合并所有参数名（保留顺序）
    all_params = required + optional
    
    # 处理 need 参数过滤
    if need is not None:
        # 标准化 need 为索引列表
        indices = _normalize_need(need, all_params)
        
        # 过滤参数
        required = [p for i, p in enumerate(required) if i in indices]
        optional = [p for i, p in enumerate(optional) if i + len(required) in indices]
    
    # 计算参数数量（如果有可变参数则为无穷）
    required_count = float('inf') if has_var_args or has_var_kwargs else len(required)
    optional_count = float('inf') if has_var_args or has_var_kwargs else len(optional)
    
    return ParamInfo(
        required=required,
        optional=optional,
        has_var_args=has_var_args,
        has_var_kwargs=has_var_kwargs,
        required_count=required_count,
        optional_count=optional_count
    )

def analyze_parameters_(obj:Any, need:Optional[Union[str,int,List[Union[str,int]]]]=None):
    """_summary_

    Args:
        obj (Any): _description_
        need (Optional[Union[str,int,List[Union[str,int]]]], optional): _description_. Defaults to None.

    Returns:
        _type_: _description_
    """
    lst = ParamInfo._fields
    lst = _normalize_need(need, lst)
    result = analyze_parameters(obj, None)
    result = [result[i] for i in lst]
    return result[0] if len(result) == 1 else result

def _normalize_need(
    need: Union[str, int, List[Union[str, int]]],
    all_params: List[str]
) -> List[int]:
    """
    标准化 need 参数为索引列表
    
    参数:
        need: 输入的过滤条件
        all_params: 所有参数名列表
        
    返回:
        参数索引列表
    """
    # 处理不同格式的 need
    if isinstance(need, int):
        items = [need]
    elif isinstance(need, str):
        # 用多种分隔符拆分字符串
        items = re.split(r'[\s,;]+', need.strip())
        # 尝试将元素转换为整数
        items = [int(item) if item.lstrip('-').isdigit() else item for item in items]
    elif isinstance(need, list):
        items = need
    else:
        return list(range(len(all_params)))
    
    # 处理每个元素
    valid_indices = set()
    max_index = len(all_params) - 1
    
    for item in items:
        if isinstance(item, int):
            # 处理负索引
            if item < 0:
                idx = len(all_params) + item
                if 0 <= idx <= max_index:
                    valid_indices.add(idx)
            # 处理正索引
            elif item <= max_index:
                valid_indices.add(item)
        elif isinstance(item, str):
            # 处理参数名
            try:
                idx = all_params.index(item)
                valid_indices.add(idx)
            except ValueError:
                continue
    
    # 返回排序后的索引列表
    return sorted(valid_indices) if valid_indices else list(range(len(all_params)))





# ============= 增强功能装饰器示例 =============
def debug_decorator(func: Callable) -> Callable:
    """调试装饰器示例"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        print(f"DEBUG: Calling {func.__name__} with args={args}, kwargs={kwargs}")
        result = func(*args, **kwargs)
        print(f"DEBUG: {func.__name__} returned {result}")
        return result
    return wrapper

def validate_args(schema: dict) -> Callable:
    """
    参数验证装饰器工厂
    
    参数:
    schema: 参数验证模式字典
    
    # 3. 带参数验证的组合
    @rcompose(
        validate_args({
            'x': {'type': int, 'min': 1, 'max': 100},
            'y': {'type': str, 'validator': lambda s: len(s) > 0}
        }),
        debug_decorator
    )
    def process_values(x: int, y: str) -> str:
        # 处理数值和字符串
        return f"Processed: {x} * {y} = {y * x}"
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 获取函数签名
            sig = inspect.signature(func)
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            params = bound.arguments
            
            # 验证参数
            for param, rules in schema.items():
                if param not in params:
                    if 'required' in rules and rules['required']:
                        raise ValueError(f"Missing required parameter: {param}")
                    continue
                    
                value = params[param]
                
                # 类型检查
                if 'type' in rules and not isinstance(value, rules['type']):
                    raise TypeError(f"Parameter {param} must be of type {rules['type']}")
                
                # 值范围检查
                if 'min' in rules and value < rules['min']:
                    raise ValueError(f"Parameter {param} must be >= {rules['min']}")
                
                if 'max' in rules and value > rules['max']:
                    raise ValueError(f"Parameter {param} must be <= {rules['max']}")
                
                # 自定义验证函数
                if 'validator' in rules:
                    if not rules['validator'](value):
                        raise ValueError(f"Parameter {param} failed validation")
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def log_exec_time(func: Callable) -> Callable:
    """执行时间记录装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()
        print(f"{func.__name__} executed in {end-start:.4f} seconds")
        return result
    return wrapper



def counting_sort(arr: List[int]):
    mx = max(arr) if arr else 0
    count = [0] * (mx + 1)
    for i in arr:
        count[i] += 1
    sorted_arr = []
    for i in range(mx + 1):
        sorted_arr += [i] * count[i]
    return sorted_arr



def swap2(*iterables, exists=None):
    if exists is None:
        exists = []
    if not iterables:
        return exists
    a, rest = iterables[0], iterables[1:]
    if isinstance(a, Iterable):
        if isinstance(a, dict):
            exists.append({frozenset(v) if isinstance(v,Iterable) else v : k for k, v in a.items()})
        else:
            a = iter(a)
            r = []
            while True:
                try:
                    m, n = next(a, None), next(a, None)
                    if m is None and n is None:
                        break
                    r.append((n, m))
                except StopIteration:
                    break
            exists.append(r)
    else:
        exists.append(None)
    return swap2(*rest, exists=exists)  # 递归调用并传递累积的exists

# print(swap2(range(9), range(10, 20), exists=[]))
# print(swap2(range(10)))
# print(swap2({'a': 1, 'b': 2, 'c': 3}, {'d': 4, 'e': 5, 'f': 6}, exists=[]))

if __name__ == '__main__':
    from random import randrange
    size = 1000000
    arr = [randrange(0,10000) for _ in range(size)]
    print(arr[:10])
    print(arr[-10:])
    from time import perf_counter
    start = perf_counter()
    sorted_arr = counting_sort(arr)
    end = perf_counter()
    print(f"Counting sort took {end-start:.4f} seconds")
    print(sorted_arr[:10])
    print(sorted_arr[-10:])
    
    
    start = perf_counter()
    sorted_arr = sorted(arr)
    end = perf_counter()
    print(f"Counting sort took {end-start:.4f} seconds")
    
    # from box import Box
    schema = {
        'x': {'type': int, 'min': 1, 'max': 100},    # 验证参数 x 的类型、最小值、最大值
        'y': {'type': str, 'validator': lambda s: len(s) > 0}    # 验证参数 y 的类型和自定义验证函数
    }
    @validate_args(schema)
    def process_values(x: int, y: str) -> str:
        # 处理数值和字符串
        return f"Processed: {x} * {y} = {y * x}"
    
    print(process_values(10, 'hello'))
    # print(process_values(1000, 'world'))
    print(process_values(x=10, y='hello'))
    # print(process_values(x=1000, y='world'))
    # print(process_values(10))
    # print(process_values(1000))
    # print(process_values(x=10))
    