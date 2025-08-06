from functools import wraps
__all__ = ['first_init']
def first_check(func=None, code_before=None, code_after=None):
    """
    装饰器：检测函数是否首次执行，并动态插入前置/后置代码
    :param func: 被装饰的函数
    :param code_before: 首次执行前调用的函数（无参数）或代码字符串
    :param code_after: 首次执行后调用的函数（无参数）或代码字符串
    :return: 装饰后的函数
    
    示例:
    def init_db():
        print("✅ 首次执行：建立数据库连接")

    def close_db():
        print("✅ 首次执行：提交事务并关闭连接")

    @first_check(code_before=init_db, code_after=close_db)
    def process_data(user_id):
        print(f"📊 处理用户 {user_id} 的数据...")

    # 测试
    process_data(1)  # 输出：建立连接 → 处理数据 → 关闭连接
    process_data(2)  # 仅输出：处理数据（跳过初始化）


    def license_check():
        print("🔐 验证许可证有效性...")

    @first_check(code_before=license_check)
    def run_algorithm():
        print("⚙️ 执行核心算法")

    run_algorithm()  # 输出：验证许可证 → 执行算法
    run_algorithm()  # 仅输出：执行算法（跳过验证）


    def start_profiler():
        print("⏱️ 启动性能监控器")

    @first_check(code_before=start_profiler)
    def heavy_computation():
        print("🧮 计算密集型任务...")

    heavy_computation()  # 首次启动监控
    heavy_computation()  # 直接执行任务
    """
    # 参数类型检查
    if code_before is not None and not (callable(code_before) or isinstance(code_before, str)):
        raise TypeError("code_before must be a callable or a string")
    if code_after is not None and not (callable(code_after) or isinstance(code_after, str)):
        raise TypeError("code_after must be a callable or a string")
    
    def decorator(f):
        f.first_runned = False  # 添加静态变量记录状态
        
        @wraps(f)
        def wrapper(*args, **kwargs):
            nonlocal code_before, code_after
            # 首次执行逻辑
            if not f.first_runned:
                # 处理前置代码
                if callable(code_before):
                    code_before()
                elif isinstance(code_before, str):
                    before_func = eval(code_before, globals(), locals())
                    if callable(before_func):
                        before_func()
                
                # 执行原函数
                result = f(*args, **kwargs)
                
                # 处理后置代码
                if callable(code_after):
                    code_after()
                elif isinstance(code_after, str):
                    after_func = eval(code_after, globals(), locals())
                    if callable(after_func):
                        after_func()
                
                # 更新状态为已执行
                f.first_runned = True
                return result
            # 非首次执行，直接返回原函数结果
            return f(*args, **kwargs)
        return wrapper
    
    # 处理直接传递函数的情况（无括号调用）
    if func is None:
        return decorator
    return decorator(func)

first_init = first_check
if __name__ == '__main__':
    def init_db():
        print("✅ 首次执行：建立数据库连接")

    def close_db():
        print("✅ 首次执行：提交事务并关闭连接")

    @first_check(code_before=init_db, code_after=close_db)
    def process_data(user_id):
        print(f"📊 处理用户 {user_id} 的数据...")

    # 测试
    process_data(1)  # 输出：建立连接 → 处理数据 → 关闭连接
    process_data(2)  # 仅输出：处理数据（跳过初始化）


    def license_check():
        print("🔐 验证许可证有效性...")

    @first_check(code_before=license_check)
    def run_algorithm():
        print("⚙️ 执行核心算法")

    run_algorithm()  # 输出：验证许可证 → 执行算法
    run_algorithm()  # 仅输出：执行算法（跳过验证）


    def start_profiler():
        print("⏱️ 启动性能监控器")

    @first_check(code_before=start_profiler)
    def heavy_computation():
        print("🧮 计算密集型任务...")

    heavy_computation()  # 首次启动监控
    heavy_computation()  # 直接执行任务