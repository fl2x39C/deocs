import time
from typing import Any, Callable, Tuple, Type, Optional, Union
from functools import wraps
import logging

__all__ = ["retry"]

def retry(
    tries: int = 3,
    delay: float = 1,
    backoff: float = 2,
    exceptions: Union[Type[Exception], Tuple[Type[Exception], ...]] = Exception,
    check_func: Optional[Callable[[Any], bool]] = None,
    logic: str = 'or',
    logger: Optional[logging.Logger] = None
) -> Callable:
    """
    增强版重试装饰器，支持多种重试条件和灵活的重试逻辑。
    
    该装饰器会在函数执行失败或返回值不满足条件时自动重试，支持多种重试逻辑组合。
    
    参数:
        tries: 最大重试次数（包括首次执行）。默认: 3
        delay: 初始延迟时间（秒）。默认: 1
        backoff: 延迟时间倍增因子。每次重试延迟 = 延迟 * backoff。默认: 2
        exceptions: 需要捕获并重试的异常类型或元组。默认: 所有异常
        check_func: 返回值检查函数，用于判断返回值是否满足条件。默认: None
        logic: 重试条件逻辑组合方式，支持以下值:
            - 'or': 异常或返回值检查失败即重试
            - 'and': 异常和返回值检查失败同时满足才重试
            - 'xor': 仅满足异常或返回值检查中的一个条件时重试
            默认: 'or'
        logger: 日志记录器实例。默认: 使用内置的print函数
    
    返回:
        装饰器函数
    
    注意事项:
        1. 当tries=1时，仅执行一次，不重试
        2. 当check_func为None时，仅依赖异常决定是否重试
        3. XOR逻辑下，异常和返回值检查只有一个条件满足时重试
        4. 当达到最大重试次数后，会抛出最后一次异常或返回最后一次结果
    
    使用示例:
    
    >>> # 基本重试示例
    >>> @retry(tries=3, delay=0.5)
    >>> def unreliable_request():
    >>>     import random
    >>>     if random.random() < 0.8:
    >>>         raise ConnectionError("网络连接失败")
    >>>     return "请求成功"
    >>>
    >>> print(unreliable_request())
    
    >>> # 返回值检查重试
    >>> @retry(tries=4, check_func=lambda x: x % 2 == 0)
    >>> def random_even():
    >>>     import random
    >>>     num = random.randint(1, 10)
    >>>     print(f"生成: {num}")
    >>>     return num
    >>>
    >>> print("结果:", random_even())
    
    >>> # 异常和返回值组合检查
    >>> @retry(tries=3, delay=1, 
    >>>         exceptions=(ConnectionError, TimeoutError),
    >>>         check_func=lambda r: r.get("status") == 200,
    >>>         logic='or')
    >>> def api_call():
    >>>     # 实现省略...
    
    >>> # XOR逻辑重试
    >>> @retry(tries=3, check_func=lambda x: x > 5, logic='xor')
    >>> def special_case():
    >>>     import random
    >>>     num = random.randint(1, 10)
    >>>     if num == 3:
    >>>         raise ValueError("特殊错误")
    >>>     return num
    >>>
    >>> print("特殊案例结果:", special_case())
    """
    # 验证逻辑参数有效性
    valid_logics = {'or', '|', '||', 'and', '&', '&&', 'xor', '^'}
    if logic not in valid_logics:
        raise ValueError(f"无效的逻辑类型: {logic}. 有效值: {valid_logics}")
    
    # 规范化逻辑关键词
    logic = 'or' if logic in {'|', '||'} else \
            'and' if logic in {'&', '&&'} else \
            'xor' if logic in {'^'} else logic
    
    # 设置日志记录器
    log = logger.info if logger else print
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            nonlocal delay
            current_delay = delay
            last_exception = None
            last_result = None
            attempt = 1
            
            while attempt <= tries:
                retry_by_exception = False
                retry_by_result = False
                result = None
                
                try:
                    # 执行目标函数
                    result = func(*args, **kwargs)
                    last_result = result
                    
                    # 检查返回值条件
                    if check_func is not None:
                        # 检查函数返回False表示需要重试
                        retry_by_result = not check_func(result)
                    
                except Exception as e:
                    # 检查异常类型是否在捕获范围内
                    if not isinstance(e, exceptions):
                        raise
                    
                    last_exception = e
                    retry_by_exception = True
                    
                    # 异常情况下返回值条件不满足
                    if check_func is not None:
                        retry_by_result = False
                
                # 根据逻辑条件判断是否重试
                if logic == 'or':
                    should_retry = retry_by_exception or retry_by_result
                elif logic == 'and':
                    should_retry = retry_by_exception and retry_by_result
                else:  # 'xor'
                    should_retry = retry_by_exception != retry_by_result
                
                # 如果不需要重试，直接返回结果
                if not should_retry:
                    return result
                
                # 如果达到最大尝试次数，不再重试
                if attempt == tries:
                    break
                
                # 记录重试信息
                retry_reason = []
                if retry_by_exception:
                    retry_reason.append(f"异常: {type(last_exception).__name__}")
                if retry_by_result:
                    retry_reason.append("返回值检查失败")
                
                log(f"尝试 {attempt}/{tries} 失败（{'，'.join(retry_reason)}），{current_delay:.2f}秒后重试...")
                
                # 等待并计算下次延迟时间
                time.sleep(current_delay)
                current_delay *= backoff
                attempt += 1
            
            # 处理最终结果
            if last_exception is not None:
                raise last_exception
            return last_result
        
        return wrapper
    
    return decorator


if __name__ == '__main__':
    # 配置日志
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("retry_decorator")
    
    # 测试1: 基本重试功能
    print("\n=== 测试1: 基本重试功能 ===")
    
    @retry(tries=3, delay=0.5, logger=logger)
    def unreliable_request():
        import random
        if random.random() < 0.8:
            raise ConnectionError("网络连接失败")
        return "请求成功"
    
    print("结果:", unreliable_request())
    
    # 测试2: 返回值检查重试
    print("\n=== 测试2: 返回值检查重试 ===")
    
    @retry(tries=4, delay=0.3, 
           check_func=lambda x: x % 2 == 0,  # 只接受偶数
           logger=logger)
    def random_even():
        import random
        num = random.randint(1, 10)
        print(f"生成: {num}")
        return num
    
    print("结果:", random_even())
    
    # 测试3: 异常和返回值组合检查
    print("\n=== 测试3: 异常和返回值组合检查 ===")
    
    def is_success(response):
        return response.get("status") == 200
    
    @retry(tries=3, delay=0.5, 
           exceptions=(ConnectionError, TimeoutError),
           check_func=is_success,
           logic='or',
           logger=logger)
    def api_call():
        import random
        scenarios = [
            {"status": 200, "data": "成功"},
            {"status": 404, "data": "未找到"},
            {"status": 500, "data": "服务器错误"},
            ConnectionError("服务不可用"),
            TimeoutError("请求超时")
        ]
        result = random.choice(scenarios)
        
        if isinstance(result, Exception):
            raise result
        return result
    
    print("API响应:", api_call())
    
    # 测试4: XOR逻辑重试
    print("\n=== 测试4: XOR逻辑重试 ===")
    
    @retry(tries=5, delay=0.2, 
           check_func=lambda x: x > 5, 
           logic='xor',
           logger=logger)
    def special_case():
        import random
        num = random.randint(1, 10)
        if num == 3:
            raise ValueError("特殊错误")
        return num
    
    print("特殊案例结果:", special_case())
    
    # 测试5: AND逻辑重试
    print("\n=== 测试5: AND逻辑重试 ===")
    
    @retry(tries=4, delay=0.3, 
           exceptions=(ValueError,),
           check_func=lambda x: x < 5, 
           logic='and',
           logger=logger)
    def and_logic_case():
        import random
        num = random.randint(1, 10)
        if num > 8:
            raise ValueError("高值错误")
        return num
    
    print("AND逻辑结果:", and_logic_case())
    
    # 测试6: 边界情况测试
    print("\n=== 测试6: 边界情况测试 ===")
    
    # 6.1: 仅执行一次
    @retry(tries=1)
    def single_try():
        return "仅执行一次"
    
    print("仅执行一次:", single_try())
    
    # 6.2: 无重试条件
    @retry()
    def no_retry_needed():
        return "不需要重试"
    
    print("无重试条件:", no_retry_needed())
    
    print("\n所有测试完成!")