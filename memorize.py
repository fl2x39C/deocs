import time
import hashlib
import pickle
from functools import wraps
cashe = {}
__all__ = ['memorize']
__doc__ = """
This module provides a memoize decorator that caches the results of a function for a specified duration.

Example usage:

```python
@memorize
def getNow():
    return time.time()

for i in range(10):
    print(getNow())
    time.sleep(1)
```

The above code will print the current time once every second, as the result of the `getNow` function is cached for 3 seconds by default.

To specify a different duration, use the `duration` parameter:

```python
@memorize(duration=5)
def getNow():
    return time.time()

for i in range(10):
    print(getNow())
    time.sleep(1)
```

To use the memoize decorator on a class method, you can use the `self` parameter:

```python
class MyClass:
    
    @memorize(duration=5)
    def getNow(self):
        return time.time()
    
    def test(self):
        for i in range(10):
            print(self.getNow())
            time.sleep(1)

    print("++++++++++++ class test ++++++++++")
    t = MyClass()
    t.test()
    print("all passed")
```

The above code will print the current time once every second, as the result of the `getNow` method is cached for 5 seconds. 

"""
def is_obsolete(entry, duration):
    return time.time() - entry['time'] > duration

def compute_key(func, args, kwargs):
    key = pickle.dumps((func.__name__, args, kwargs))
    return hashlib.sha256(key).hexdigest()

def memorize(func=None,duration=3):
    @wraps(func)
    def wrapper(func):
        def _wrapper(*args, **kwargs):
            key = compute_key(func, args, kwargs)
            if key in cashe and not is_obsolete(cashe[key], duration):
                # print('cache hit')
                return cashe[key]['result']
            result = func(*args, **kwargs)
            cashe[key] = {'result': result, 'time': time.time()}
            return result
        return _wrapper
    if func:
        return wrapper(func)
    return wrapper

if __name__ == '__main__':
    @memorize
    def getNow1():
        
        return time.time()

    for i in range(10):
        print(getNow1())
        time.sleep(1)

    @memorize(duration=5)
    def getNow():
        return time.time()

    for i in range(10):
        print(getNow())
        time.sleep(1)


    class MyClass:
        
        @memorize(duration=5)
        def getNow(self):
            return time.time()
        
        def test(self):
            for i in range(10):
                print(self.getNow())
                time.sleep(1)

    print("++++++++++++ class test ++++++++++")
    t = MyClass()
    t.test()
    print("all passed")