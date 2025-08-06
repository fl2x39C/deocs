import inspect
from functools import wraps,update_wrapper

__all__ = ['iterable']

def iterable(obj=None, predicate=None, cache=False):
    """
    将一个函数或对象转换为可迭代对象，支持缓存和停止条件
    
    参数:
    obj: 被装饰的函数或可迭代对象（非函数时直接返回迭代器）
    predicate: 停止条件函数，当返回True时停止迭代（可选）
    cache: 是否缓存函数的第一次返回值（可选，默认为False）
    
    返回值:
    生成器对象或原始对象的迭代器
    
    示例:
    
    1. 普通函数转换为生成器
    >>> import random
    >>> @iterable(predicate=lambda x: x < 0)
    ... def random_with_negative():
    ...     return random.randint(-10, 10)
    ...
    >>> random.seed(42)
    >>> result = list(random_with_negative)
    >>> print(f"测试1 - 生成数量: {len(result)}, 结果: {result}")
    测试1 - 生成数量: 3, 结果: [8, 1, -10]
    
    2. 使用缓存功能
    >>> @iterable(cache=True)
    ... def counter():
    ...     return random.randint(1, 100)
    ...
    >>> random.seed(123)
    >>> values = [next(counter) for _ in range(3)]
    >>> print(f"测试2 - 缓存值: {values}")
    测试2 - 缓存值: [97, 97, 97]
    
    3. 同时使用谓词和缓存
    >>> @iterable(predicate=lambda x: x == 0, cache=True)
    ... def random_with_zero():
    ...     return random.randint(-1, 1)
    ...
    >>> random.seed(456)
    >>> result = list(random_with_zero)
    >>> print(f"测试3 - 生成数量: {len(result)}, 结果: {result}")
    测试3 - 生成数量: 2, 结果: [1, 0]
    
    4. 处理生成器函数（直接返回生成器本身）
    >>> @iterable(predicate=lambda x: x > 3)
    ... def my_generator():
    ...     for i in range(1, 6):
    ...         yield i
    ...
    >>> list(my_generator)  # 谓词对生成器无效
    [1, 2, 3, 4, 5]
    
    5. 处理非函数对象（直接返回迭代器）
    >>> for item in iterable([1, 2, 3]):
    ...     print(item)
    1
    2
    3
    """
    # 处理普通可迭代对象（非callable）
    if obj is not None and not callable(obj):
        return iter(obj) if not isinstance(obj,dict) else iter(obj.items())
    
    def decorator(f):
        # 检查是否是生成器函数
        
        if inspect.isgeneratorfunction(f):
            # 如果是生成器函数，直接返回生成器对象
            gen = f()
            # update_wrapper(gen, f,assigned=filter(lambda x: x not in ('__call__','__module__', '__name__', '__qualname__', '__doc__','__annotations__'), dir(f)))
            return gen
        
        last_value = None
        first_run = True
        
        @wraps(f)
        def wrapper():
            nonlocal last_value, first_run
            # 处理缓存逻辑：仅当cache=True且没有谓词时才使用缓存
            if cache and predicate is None and not first_run:
                return last_value
            
            # 计算新值
            value = f()
            # 仅当cache=True且没有谓词时才缓存
            if cache and predicate is None:
                last_value = value
            first_run = False
            return value
        
        def gen():
            while True:
                value = wrapper()
                yield value
                # 返回值后检查停止条件
                if predicate and predicate(value):
                    break
        
        # 返回生成器对象
        return gen()
    
    # 处理无参调用
    if obj is None:
        return decorator
    
    # 处理有参调用
    return decorator(obj)


if __name__ == '__main__':
    import random
    @iterable(predicate=lambda x: x < 0)
    def my_func():
        return random.randint(-10, 10)

    print(list(my_func))

    for item in iterable([1, 2, 3]):
        print(item)
    
    print(list(iterable("sdfsdfwefw")))
        
    @iterable
    def my_generator():
        for i in range(5):
            yield i
            
    print(list(my_generator))
    
    
    from decoFactory import static_vars
    
    
    counter = 0
    # @static_vars(counter=0)
    @iterable(predicate=lambda x: x > 9)
    def my_counter():
        global counter
        counter += 1
        return counter
    
    for i in my_counter:
        print(i)
    
    # @iterable(cache=True)
    # @static_vars(counter=0)
    # def gen():
    #     while 1:
    #         yield gen.counter
    #         gen.counter += 1
    # print('------.*------')    
    # y = gen
    # for i in y:
    #     print(i,end=' ')
    #     if i > 10:
    #         break
        
        
    
    @iterable(cache=True)
    def fb():
        a = 0
        b = 1
        while 1:
            yield a
            # print(a,b)
            a, b = b, a + b
    print('------.*------')    
    for i in fb:
        # print(i,end=' ')
        if i > 10:    
            break
        
    for i in fb:
        print(i,end=' ')
        if i > 10:    
            break
        
    print(next(fb))