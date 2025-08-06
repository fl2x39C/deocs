from time import time
from inspect import signature,isclass
__all__ = ["once"]


class _OnceWrapper:
    __slots__ = ("func", "called", "result", "force", "called_args", "called_kwargs", "last_called_time")
    def __init__(self, func):
        self.func = func
        self.called = False
        self.result = None
        self.force = False
        self.called_args = None
        self.called_kwargs = None
        self.last_called_time = None
        __signature__ = signature(func)
    
    def __call__(self, *args, **kwds):
        force = kwds.pop("force", False)
        if force:
            self.force = True
        if self.called and not self.force:
            return self.result
        self.called_args = args
        self.called_kwargs = kwds
        self.called = True
        self.force = False
        self.result = self.func(*args, **kwds)
        self.last_called_time = time()
        return self.result


def once(obj):
    # 处理类装饰
    if isclass(obj):
        class Singleton(obj):
            _instance = None
            def __new__(cls, *args, **kwargs):
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
                return cls._instance
            
            def __init__(self, *args, **kwargs):
                if not self._initialized:
                    super().__init__(*args, **kwargs)
                    self._initialized = True
        
        # 复制原始类的属性
        Singleton.__name__ = obj.__name__
        Singleton.__qualname__ = obj.__qualname__
        Singleton.__doc__ = obj.__doc__
        Singleton.__module__ = obj.__module__
        return Singleton
    
    # 处理函数装饰
    return _OnceWrapper(obj)

if __name__ == "__main__":
    @once
    def add(a, b):
        return a + b
    print(add(1, 2))
    print(add(1, 3))
    print(add(1, 4))
    print(add.result,add.last_called_time,add.called_args,add.called_kwargs)
    print(add(1, 4,force=True))
    print(add.result,add.last_called_time,add.called_args,add.called_kwargs)
    
    
    @once
    class A:
        def __init__(self, x):
            self.x = x
        @property
        @once
        def y(self):
            return self.x + 1
    
        def print(self):
            print(self.x, self.y)


    @once
    class B:
        def __init__(self, x):
            self.x = x

    a1 = A(1)
    a2 = A(2)
    assert a1 == a2 == A(3)
    a1.print()
    a2.print()
    a1.print()
    print(type(A), A.__name__,A.__qualname__,A)
    b1 = B(1)
    b2 = B(2)
    assert b1 == b2 == B(3)
    print(type(B), B.__name__,B.__qualname__,B)
    assert isinstance(a1, A)
    assert isinstance(b1, B)
    assert not isinstance(a1, B)
    assert not isinstance(b1, A)