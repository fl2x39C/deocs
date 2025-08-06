from collections import OrderedDict, namedtuple
from functools import partial, update_wrapper
import inspect as ins
import types
from decoFactory import run_all  # 导入装饰器工厂
import math

ParamsInfo = namedtuple('ParamsInfo', ['required', 'optional','has_var_args','has_var_kwargs'])

def count_constructor_params(cls):
    """
    获取类构造函数(__init__)的参数统计信息
    :param cls: 类对象
    :return: 元组 (必选参数个数, 可选参数个数)
             若存在 *args 或 ​**kwargs，可选参数返回 math.inf（无限）
    """
    # 检查类是否有自定义__init__
    if ins.isclass(cls):
        if not hasattr(cls, '__init__') or cls.__init__ is object.__init__:
            return ParamsInfo(0, 0, False, False)
        # 获取__init__签名
        sig = ins.signature(cls.__init__)
    elif ins.isfunction(cls):
        sig = ins.signature(cls)
    else:
        raise TypeError("Invalid class or function")
    required = 0
    optional = 0
    has_var_args = False
    has_var_kwargs = False

    for name, param in sig.parameters.items():
        # 跳过self参数
        if name == 'self':
            continue
        
        # 检测可变参数
        if param.kind == param.VAR_POSITIONAL:
            has_var_args = True
        elif param.kind == param.VAR_KEYWORD:
            has_var_kwargs = True
        # 必选参数（无默认值且非可变参数）
        elif param.default == param.empty:
            required += 1
        # 可选参数（有默认值）
        else:
            optional += 1
    
    # 处理可变参数的特殊情况
    if has_var_args or has_var_kwargs:
        optional = math.inf
    
    return ParamsInfo(required, optional, has_var_args, has_var_kwargs)
# 定义类元数据结构



def eval_expr_in_data(data, context):
    """
    递归处理数据结构中的表达式（以'->'开头的字符串）
    支持列表、元组、字典、集合等嵌套结构
    """
    try:
        if isinstance(data, str) and data.startswith('->'):
            # 执行表达式并返回结果
            expr = data[2:].strip()
            return eval(expr, context)
        elif isinstance(data, (list, tuple)):
            # 递归处理序列中的每个元素
            return type(data)(eval_expr_in_data(item, context) for item in data)
        elif isinstance(data, dict):
            # 递归处理字典的键和值
            return {
                eval_expr_in_data(k, context): eval_expr_in_data(v, context)
                for k, v in data.items()
            }
        elif isinstance(data, set):
            # 递归处理集合中的每个元素
            return {eval_expr_in_data(item, context) for item in data}
        else:
            # 非表达式和非容器类型直接返回
            return data
    except Exception as e:
        # 在表达式求值出错时提供详细错误信息
        exc_type, exc_value, exc_traceback = sys.exc_info()
        tb_details = traceback.format_exception(exc_type, exc_value, exc_traceback)
        error_msg = f"Error evaluating expression: {data}\n{tb_details}"
        raise RuntimeError(error_msg)

# 定义类元数据结构
ClsMeta = namedtuple('ClsMeta', [
    'priority',      # 优先级（数值越小优先级越高）
    'init_func',     # 初始化函数
    'init_args',     # 初始化位置参数
    'init_kwargs',   # 初始化关键字参数
    'need_cache'     # 是否缓存实例
])

def cls_mixer(*search_classes, **kwargs):
    """
    类混合器 - 动态属性融合装饰器
    
    特性：
    1. 分离类元数据(ClsMeta)和属性元数据
    2. 支持类级别和方法级别的独立配置
    3. 智能处理属性访问和方法调用
    4. 支持属性优先级管理
    5. 自动处理描述符属性（如@property）
    
    配置格式：
    - 类级别配置：{cls_name}__{key}
    - 方法级别配置：{cls_name}__{method_name}__{key}
    
    示例：
    @cls_mixer(MyClass, 
        MyClass__priority=10,
        MyClass__init_args=(1, 2),
        MyClass__my_method__code_first="print('Before call')"
    )
    class MyWrapper: ...
    """
    
    def decorator(cls):
        class Wrapper(cls):
            # 类级存储（所有实例共享）
            _cls_meta = OrderedDict()    # cls_name -> ClsMeta
            _attr_config = OrderedDict()  # (cls_name, attr_name) -> run_all配置
            
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                # 实例级存储（每个实例独立）
                self._instance_cache = OrderedDict()
                self._attr_cache = OrderedDict()
                # 初始化类配置
                self._init_class_config()
            
            def _init_class_config(self):
                """初始化类配置"""
                for target_cls in search_classes:
                    if target_cls is None:
                        continue
                    
                    if ins.isclass(target_cls):
                        cls_name = target_cls.__name__
                    elif isinstance(target_cls, object):
                        cls_name = target_cls.__class__.__name__
                        self._instance_cache[cls_name] = target_cls
                    else:
                        raise TypeError("Invalid target class")
                    
                    # 提取类级别配置
                    prefix = f"{cls_name}__"
                    cls_config = {k.replace(prefix, ''): v 
                                 for k, v in kwargs.items() 
                                 if k.startswith(prefix) and '__' not in k[len(prefix):]}
                    
                    # 创建类元数据
                    self._cls_meta[cls_name] = ClsMeta(
                        priority=cls_config.get('priority', 50),
                        init_func=cls_config.get('init_func', target_cls),
                        init_args=cls_config.get('init_args', ()),
                        init_kwargs=cls_config.get('init_kwargs', {}),
                        need_cache=cls_config.get('need_cache', True)
                    )
                    
                    # 扫描类属性，提取方法级别配置
                    for attr_name, attr_value in ins.getmembers(target_cls):
                        if attr_name.startswith('__') and attr_name.endswith('__'):
                            continue
                            
                        # 方法级别配置前缀
                        attr_prefix = f"{cls_name}__{attr_name}__"
                        attr_config = {k.replace(attr_prefix, ''): v 
                                      for k, v in kwargs.items() 
                                      if k.startswith(attr_prefix)}
                        
                        # 创建属性配置（使用run_all兼容格式）
                        if attr_config:
                            # 映射到run_all参数
                            config_map = {
                                'params_modify_func': attr_config.get('params_modify_func', None),
                                'params_check_func': attr_config.get('params_check_func', None),
                                'code_first': attr_config.get('code_first', None),
                                'code_last': attr_config.get('code_last', None),
                                'result_func': attr_config.get('result_func', None),
                                'result_check_info': attr_config.get('result_check_info', None),
                                'log_all_info': attr_config.get('log_all_info', None)
                            }
                            
                            # 处理部分参数（转换为参数修改函数）
                            partial_args = attr_config.get('partial_args', ())
                            partial_kwargs = attr_config.get('partial_kwargs', {})
                            
                            if partial_args or partial_kwargs:
                                def partial_wrapper(args, kws):
                                    # 在调用时对表达式求值
                                    context = {
                                        'self': self,
                                        '_cls_meta': self._cls_meta,
                                        '_attr_config': self._attr_config
                                    }
                                    evaluated_args = eval_expr_in_data(partial_args, context)
                                    evaluated_kwargs = eval_expr_in_data(partial_kwargs, context)
                                    return (tuple(evaluated_args) + args, {**evaluated_kwargs, **kws})
                                
                                config_map['params_modify_func'] = partial_wrapper
                            
                            self._attr_config[(cls_name, attr_name)] = config_map
            
            def _get_target_instance(self, cls_name):
                """获取或创建目标类的实例"""
                # 检查缓存
                if cls_name in self._instance_cache:
                    return self._instance_cache[cls_name]
                
                # 获取类元数据
                cls_meta = self._cls_meta.get(cls_name)
                if cls_meta is None:
                    raise ValueError(f"Class '{cls_name}' not configured")
                
                # 对init_args和init_kwargs中的表达式求值
                context = {
                    'self': self,
                    '_cls_meta': self._cls_meta,
                    '_attr_config': self._attr_config
                }
                init_args = eval_expr_in_data(cls_meta.init_args, context)
                init_kwargs = eval_expr_in_data(cls_meta.init_kwargs, context)
                
                # 智能初始化（使用求值后的参数）
                for _ in [1]:
                    try:
                        clsOfInit = cls_meta.init_func
                        ps = count_constructor_params(clsOfInit)
                        mx = ps[0] + ps[1]
                        mn = ps[0]
                        if mx + mn == 0:
                            instance = clsOfInit()
                            break
                        if ps[2] and ps[3]:
                            instance = clsOfInit(*init_args, **init_kwargs)
                            break
                        k1, k2 = len(init_args), len(init_kwargs)
                        kn = k1 + k2
                        
                        if mn > kn:
                            raise TypeError(f"Missing {mn-kn} required positional arguments !!!")
                        if k1 >= mn and kn > mx:
                            instance = clsOfInit(*init_args[:mx], **init_kwargs)
                            break
                        if k1 > mx:
                            instance = clsOfInit(*init_args[:mx])
                            break
                        if k2 > mx:
                            instance = clsOfInit(**init_kwargs)
                            break
                        try:
                            instance = clsOfInit(*init_args, **init_kwargs)
                            break
                        except TypeError:
                            if ps[2]:
                                instance = clsOfInit(*init_args)
                                break
                            if ps[3]:
                                instance = clsOfInit(**init_kwargs)
                                break
                            if k2 > 0:
                                raise TypeError(f"Missing {k2} required keyword-only arguments")
                            if k1 < mn:
                                raise TypeError(f"Missing {mn-k1} required positional arguments")
                            if k2 < k1-mn:
                                raise TypeError(f"Got {k1-mn} unexpected keyword-only arguments")
                            if k1 > mx:
                                raise TypeError(f"Got {k1-mx} unexpected positional arguments")
                            raise TypeError(f"Unknown error when initializing '{cls_name}'")

                    except Exception as e:
                        raise RuntimeError(
                            f"Failed to initialize '{cls_name}': {str(e)} -> {ps} -> len_args: {k1}, len_kwargs: {k2}"
                        )
                
                # 缓存实例
                if cls_meta.need_cache:
                    self._instance_cache[cls_name] = instance
                
                return instance
            
            def __getattr__(self, name):
                """动态属性访问"""
                # 检查属性缓存
                if name in self._attr_cache:
                    return self._attr_cache[name]
                
                # 遍历所有类寻找属性
                for cls_name in self._cls_meta:
                    try:
                        # 获取目标实例
                        target_obj = self._get_target_instance(cls_name)
                        
                        # 获取原始属性
                        attr = getattr(target_obj, name)
                        
                        # 处理普通方法
                        if callable(attr):
                            # 获取属性配置
                            attr_config = self._attr_config.get((cls_name, name), {})
                            
                            # 使用run_all创建包装方法
                            wrapped = run_all(**attr_config)(attr)
                            
                            # 更新包装方法的元数据
                            update_wrapper(wrapped, attr)
                            wrapped.__name__ = f"{cls_name}_{name}"
                            
                            self._attr_cache[name] = wrapped
                            return wrapped
                        
                        # 非可调用属性直接返回
                        self._attr_cache[name] = attr
                        return attr
                        
                    except AttributeError:
                        continue
                
                raise AttributeError(
                    f"'{self.__class__.__name__}' object has no attribute '{name}'"
                )
            
            # ===== 动态管理接口 =====
            def add_class(self, target_cls, priority=None, init_func=None, 
                         init_args=(), init_kwargs={}, need_cache=True):
                """添加新的融合类"""
                # ...（保持不变）...
            
            def update_class_config(self, cls_name, **new_config):
                """更新类配置"""
                # ...（保持不变）...
            
            def update_attr_config(self, cls_name, attr_name, **new_config):
                """更新属性配置"""
                key = (cls_name, attr_name)
                # 创建或更新属性配置（使用run_all格式）
                if key not in self._attr_config:
                    self._attr_config[key] = {}
                
                # 映射配置项
                config_map = {
                    'params_modify_func': 'params_modify_func',
                    'params_check_func': 'params_check_func',
                    'code_first': 'code_first',
                    'code_last': 'code_last',
                    'result_func': 'result_func',
                    'result_check_info': 'result_check_info',
                    'log_all_info': 'log_all_info'
                }
                
                for k, v in new_config.items():
                    if k in config_map:
                        self._attr_config[key][config_map[k]] = v
                
                # 清除属性缓存
                if attr_name in self._attr_cache:
                    del self._attr_cache[attr_name]

            def __dir__(self):
                """增强目录方法"""
                base_dir = set(super().__dir__())
                
                # 添加动态属性
                dynamic_attrs = set()
                for cls_name in self._cls_meta:
                    try:
                        target_obj = self._get_target_instance(cls_name)
                        dynamic_attrs.update(dir(target_obj))
                    except Exception:
                        continue
                
                return sorted(base_dir | dynamic_attrs)
            
            def get_class_priority(self, cls_name):
                """获取类的优先级"""
                if cls_name in self._cls_meta:
                    return self._cls_meta[cls_name].priority
                return None
            
            def get_priority_classes(self):
                """按优先级排序返回类列表"""
                return sorted(
                    self._cls_meta.keys(),
                    key=lambda x: self._cls_meta[x].priority
                )
        
        return Wrapper
    
    return decorator