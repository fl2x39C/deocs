

from concurrent.futures import ThreadPoolExecutor,ProcessPoolExecutor
from collections.abc import Iterable
from functools import wraps

__all__ = ['trd','vic_execute','for_','proc']
def vic_execute(func=None,max_workers=3,use_process = False):
    def decorator(func):
        @wraps(func)
        def wrapper(iterable):
            its = iterable if isinstance(iterable,Iterable) else [iterable]

            pool = ProcessPoolExecutor if use_process else ThreadPoolExecutor

            with pool(max_workers=max_workers) as executor:
                # futures = [ executor.submit(func, x) for x in its ]
                # results = [ future.result() for future in as_completed(futures)]
                results = [ furture for furture in executor.map(func,its) ]
            return results
        return wrapper
    return decorator if func is None else decorator(func)

trd = vic_execute(max_workers=10,use_process=0)
for_ = vic_execute(max_workers=1,use_process=0)
proc = vic_execute(max_workers=3,use_process=1)

if __name__ == "__main__":
    from time import sleep,time
    @vic_execute(max_workers=100,use_process=0)
    def add(x):
        sleep(0.1)
        return x + 1

    t=time()
    add(range(100))
    print(time()-t)
    
    @trd
    def add(x):
        sleep(0.1)
        return x + 1

    t=time()
    add(range(100))
    print(time()-t)
        
        
    from time import sleep,time
    def add3(x):
        sleep(0.1)
        return x + 1

    t=time()
    print(proc(add3)(range(100000000)))
    print(time()-t)