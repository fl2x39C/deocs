
from typing import Any, Callable, Optional, Tuple, Type, Union
from functools import wraps
import logging
import sys
import traceback

__all__ = ["ignore_errs", "print_exceptions"]

def ignore_errs(
    errors: Union[Type[Exception]], 
    defaults: Any = None
) -> Callable:
    """
    高级错误忽略装饰器
    
    参数:
        errors: 错误类型或错误类型列表/元组
        defaults: 对应错误的默认值或默认值列表
        
    功能:
        捕获指定类型的错误并返回对应的默认值
        
        

    # 错误组和不同默认值
    @ignore_errs(
        errors=[
            [ZeroDivisionError, OverflowError],  # 数学错误组
            FileNotFoundError,                   # 文件错误
            [KeyError, IndexError]               # 键/索引错误组
        ],
        defaults=[
            "数学错误", 
            "文件未找到", 
            "键/索引错误"
        ]
    )
    def complex_operation(data):
        # 模拟各种可能发生的错误
        if "file" in data:
            raise FileNotFoundError("文件缺失")
        if "key" not in data:
            raise KeyError("缺少键")
        if data["index"] > len(data["items"]):
            raise IndexError("索引越界")
        if data["divisor"] == 0:
            raise ZeroDivisionError("除零错误")
        return "成功"

    data1 = {"divisor": 0}
    print(complex_operation(data1))  # "数学错误"

    data2 = {"file": "missing.txt"}
    print(complex_operation(data2))  # "文件未找到"

    data3 = {"index": 5, "items": [1,2,3]}
    print(complex_operation(data3))  # "键/索引错误"

    # 混合使用标量和列表
    @ignore_errs(
        errors=ZeroDivisionError,  # 单个错误类型
        defaults=["除零错误"]       # 单个默认值（自动扩展）
    )
    def divide(a, b):
        return a / b

    print(divide(10, 0))  # "除零错误"

    # 不等长处理
    @ignore_errs(
        errors=[TypeError, ValueError, KeyError],
        defaults=["类型错误"]  # 单个值自动扩展到所有错误
    )
    def handle_data(value):
        if isinstance(value, str):
            raise TypeError("字符串无效")
        if value < 0:
            raise ValueError("负数无效")
        return value

    print(handle_data("test"))  # "类型错误"
    print(handle_data(-5))      # "类型错误" (自动扩展)
    """
    # 标准化错误类型和默认值
    if not isinstance(errors, (list, tuple)):
        errors = [errors]
    
    if not isinstance(defaults, (list, tuple)):
        defaults = [defaults] * len(errors)
    elif len(defaults) != len(errors):
        # 如果默认值列表长度不匹配，复制最后一个值填充
        defaults = list(defaults) + [defaults[-1]] * (len(errors) - len(defaults))
    
    # 构建错误类型到默认值的映射
    error_map = {}
    for i, err_type in enumerate(errors):
        if isinstance(err_type, (list, tuple)):
            # 处理错误类型组
            for et in err_type:
                error_map[et] = defaults[i]
        else:
            error_map[err_type] = defaults[i]
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # 查找匹配的错误类型
                for err_type, default_val in error_map.items():
                    if isinstance(e, err_type):
                        return default_val
                
                # 如果设置了默认捕获所有错误
                if Exception in error_map:
                    return error_map[Exception]
                
                # 没有匹配的错误类型，重新抛出异常
                raise
        
        return wrapper
    
    return decorator






def print_exceptions(
    filepath: Optional[str] = None,
    last_error_only: bool = True,
    log_level: str = "ERROR",
    ignore_errors: Optional[Union[Type[Exception], Tuple[Type[Exception], ...]]] = None
):
    """
    增强版异常打印装饰器
    
    参数:
        filepath: 异常信息输出文件路径
        last_error_only: 是否只打印最后一个异常
        log_level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        ignore_errors: 忽略的异常类型（不打印）
        
        
    @print_exceptions(
        filepath="advanced_errors.log",
        log_level="WARNING",
        ignore_errors=(KeyboardInterrupt,))
    def critical_operation(data):
        if data < 0:
            raise ValueError("负数无效")
        return data ** 2

    critical_operation(-5)

    """
    # 映射日志级别
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }
    log_level_value = level_map.get(log_level.upper(), logging.ERROR)
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # 检查是否需要忽略此异常
                if ignore_errors and isinstance(e, ignore_errors):
                    raise
                
                # 设置日志记录器
                logger = logging.getLogger(func.__name__)
                logger.setLevel(log_level_value)
                
                # 添加文件处理器（如果需要）
                if filepath:
                    file_handler = logging.FileHandler(filepath, encoding='utf-8')
                    file_handler.setFormatter(logging.Formatter(
                        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                    ))
                    logger.addHandler(file_handler)
                else:
                    # 默认输出到控制台
                    console_handler = logging.StreamHandler(sys.stderr)
                    console_handler.setFormatter(logging.Formatter(
                        '[%(levelname)s] %(message)s'
                    ))
                    logger.addHandler(console_handler)
                
                # 构建日志消息
                message = f"函数 {func.__name__} 执行失败\n"
                message += f"参数: args={args}, kwargs={kwargs}\n"
                
                if last_error_only:
                    message += f"异常: {type(e).__name__}: {str(e)}"
                else:
                    message += "完整堆栈跟踪:\n" + ''.join(traceback.format_exc())
                
                # 记录日志
                logger.log(log_level_value, message)
                
                # 清理处理器
                if filepath:
                    logger.removeHandler(file_handler)
                else:
                    logger.removeHandler(console_handler)
                
                raise
        
        return wrapper
    return decorator

