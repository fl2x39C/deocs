import enum
import inspect
import types
import functools

__all__ = ['CallableType','get_callable_type','create_fake']




class CallableType(enum.Enum):
    """可调用对象类型枚举（按判断顺序排列）"""
    # 可调用类型
    CALLABLE_CLASS = 0              # 类（可调用，用于创建实例）
    CALLABLE_CLASSMETHOD = 1        # 类方法
    CALLABLE_INSTANCEMETHOD = 2     # 实例方法
    CALLABLE_STATICMETHOD = 3       # 静态方法
    CALLABLE_FUNCTION = 4           # 普通函数
    CALLABLE_INSTANCE = 5           # 可调用的实例（实现了__call__）
    
    # 不可调用类型
    NOT_CALLABLE_INSTANCE_ATTR = 6  # 不可调用的实例属性
    NOT_CALLABLE_INSTANCE = 7       # 不可调用的实例
    
    # 未知类型
    UNKNOWN = -1                    # 未知类型
    
    def __iter__(self):
        return super().__iter__()

def get_callable_type(obj):
    """
    判断对象的可调用类型，返回对应的CallableType枚举值
    判断顺序与枚举顺序一致
    """
    # 1. 检查是否是类（可调用）
    if inspect.isclass(obj):
        return CallableType.CALLABLE_CLASS
    
    # 2. 检查是否是类方法
    if inspect.ismethod(obj) and inspect.isclass(obj.__self__):
        return CallableType.CALLABLE_CLASSMETHOD
    
    # 3. 检查是否是实例方法
    if inspect.ismethod(obj) and not inspect.isclass(obj.__self__):
        return CallableType.CALLABLE_INSTANCEMETHOD
    
    # 4. 检查是否是静态方法
    if isinstance(obj, staticmethod):
        return CallableType.CALLABLE_STATICMETHOD
    
    # 检查通过类访问的静态方法（函数形式）
    try:
        if inspect.isfunction(obj):
            # 通过__qualname__判断是否为类的静态方法
            qualname_parts = obj.__qualname__.split('.')
            if len(qualname_parts) >= 2:
                class_name = qualname_parts[0]
                method_name = qualname_parts[-1]
                module = inspect.getmodule(obj)
                if module and hasattr(module, class_name):
                    cls = getattr(module, class_name)
                    # 直接访问类字典获取原始属性，避免自动解包staticmethod
                    class_attr = cls.__dict__.get(method_name)
                    if isinstance(class_attr, staticmethod):
                        return CallableType.CALLABLE_STATICMETHOD
    except Exception:
        pass

    # 5. 检查是否是普通函数
    if inspect.isfunction(obj) or isinstance(obj, types.BuiltinFunctionType):
        return CallableType.CALLABLE_FUNCTION
    
    # 6. 检查是否是可调用实例
    if callable(obj) and hasattr(obj, '__class__') and not inspect.isclass(obj):
        return CallableType.CALLABLE_INSTANCE
    
    # 7. 检查是否是不可调用的实例属性
    if (not callable(obj) and 
        hasattr(obj, '__class__') and 
        obj.__class__.__module__ == 'builtins' and 
        not inspect.isclass(obj)):
        return CallableType.NOT_CALLABLE_INSTANCE_ATTR
    
    # 8. 检查是否是不可调用的实例
    if (not callable(obj) and 
        hasattr(obj, '__class__') and 
        not inspect.isclass(obj)):
        return CallableType.NOT_CALLABLE_INSTANCE
    
    # 9. 未知类型
    return CallableType.UNKNOWN

def create_fake(func):
    # 如果传入的是类，则处理其 __init__ 方法
    if inspect.isclass(func):
        target = func.__init__
    else:
        target = func
    
    # 获取目标函数的签名
    try:
        sig = inspect.signature(target)
    except (ValueError, TypeError):
        # 处理无法获取签名的内置函数
        sig = inspect.Signature()
    
    # 构建新函数的参数列表
    params = []
    for name, param in sig.parameters.items():
        # 保留参数类型（位置参数、关键字参数等）
        new_param = inspect.Parameter(
            name=name,
            kind=param.kind,
            default=param.default,
            annotation=param.annotation
        )
        params.append(new_param)
    
    # 创建新函数的签名
    new_sig = sig.replace(parameters=params)
    
    # 使用 functools.wraps 复制元数据
    @functools.wraps(target)
    def wrapper(*_, **__):
        return get_callable_type(func)

    
    # 保留原始签名
    wrapper.__signature__ = new_sig
    return wrapper

# 测试代码保持不变


def test_callable_type_detection():
    """测试get_callable_type函数的正确性"""
    # 测试类
    class TestClass:
        class_attr = 10
        
        def instance_method(self):
            pass
        
        @classmethod
        def class_method(cls):
            pass
        
        @staticmethod
        def static_method():
            pass
        
    class CallableInstance:
        def __call__(self):
            pass
    
    # 普通函数
    def normal_function():
        pass
    
    # 测试实例TestClass.static_method
    test_obj = TestClass()
    callable_obj = CallableInstance()
    print(get_callable_type(TestClass.static_method))
    print(get_callable_type(test_obj.static_method))
    print(isinstance(TestClass.static_method,staticmethod))
    print(isinstance(test_obj.static_method,staticmethod))
    print(dir(test_obj.static_method))
    print(dir(test_obj.static_method))
    

    # 测试用例列表
    test_cases = [
        (TestClass, CallableType.CALLABLE_CLASS, "类检测"),
        (TestClass.class_method, CallableType.CALLABLE_CLASSMETHOD, "类方法检测"),
        (test_obj.instance_method, CallableType.CALLABLE_INSTANCEMETHOD, "实例方法检测"),
        (TestClass.static_method, CallableType.CALLABLE_STATICMETHOD, "静态方法检测"),
        (normal_function, CallableType.CALLABLE_FUNCTION, "普通函数检测"),
        (callable_obj, CallableType.CALLABLE_INSTANCE, "可调用实例检测"),
        (test_obj.class_attr, CallableType.NOT_CALLABLE_INSTANCE_ATTR, "不可调用实例属性检测"),
        (test_obj, CallableType.NOT_CALLABLE_INSTANCE, "不可调用实例检测"),
        (123, CallableType.NOT_CALLABLE_INSTANCE_ATTR, "内置类型实例检测"),
        ("string", CallableType.NOT_CALLABLE_INSTANCE_ATTR, "字符串实例检测"),
        ([], CallableType.NOT_CALLABLE_INSTANCE_ATTR, "列表实例检测"),
        ({}, CallableType.NOT_CALLABLE_INSTANCE_ATTR, "字典实例检测"),
        (None, CallableType.NOT_CALLABLE_INSTANCE_ATTR, "None类型检测"),
    ]
    
    # 执行测试
    passed = 0
    failed = 0
    
    for obj, expected_type, test_name in test_cases:
        try:
            result = get_callable_type(obj)
            assert result == expected_type
            f"预期: {expected_type}, 实际: {result}"
            print(f"✅ {test_name} 通过")
            passed += 1
        except AssertionError as e:
            print(f"❌ {test_name} 失败: {str(e)}")
            failed += 1
    
    print(f"\n测试完成: 通过 {passed} 项, 失败 {failed} 项")
    return passed, failed


if __name__ == '__main__':
    test_callable_type_detection()




    # 测试普通函数
    def example_func(a: int, b: str = "default") -> bool:
        return True

    fake_func = create_fake(example_func)
    print(inspect.signature(fake_func))  # 输出: (a: int, b: str = 'default') -> None
    print(fake_func(1, "test"))          # 输出: None

    # 测试类
    class ExampleClass:
        def __init__(self, x: float, y: int = 0):
            pass

    fake_class_init = create_fake(ExampleClass)
    print(inspect.signature(fake_class_init))  # 输出: (self, x: float, y: int = 0) -> None

    # 测试实现了 __call__ 的类实例
    class CallableClass:
        def __call__(self, a, b=10):
            return a + b

    callable_instance = CallableClass()
    fake_call = create_fake(callable_instance)
    print(inspect.signature(fake_call))  # 输出: (a, b=10) -> None


