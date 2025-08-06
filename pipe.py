import functools
import itertools
import sys
from collections import deque
from collections.abc import Iterable
from functools import wraps
from holder import _ , lazy, gene_func

__all__ = ['Pipe', 'Ops','NONE','_','gene_func','lazy']

def _transform(func):
    if isinstance(func, str) and ("->" in func or "=>" in func):
        func = lazy(func)
    return func

class Pipe:
    def __init__(self, func, *args, **kwargs):
        func = _transform(func)
        self.raw_func = func
        self.func = lambda iterable, *args2, **kwargs2: func(
            iterable, *args, *args2, **kwargs, **kwargs2
        )
        functools.update_wrapper(self, func)
        
    def __ror__(self, other):
        return self.func(other)
    
    def __ilshift__(self, other):
        return self.compose(self.raw_func, other.raw_func if isinstance(other, Pipe) else _transform(other))
    
    def __irshift__(self, other):
        return self.pipe(self.raw_func, other.raw_func if isinstance(other, Pipe) else _transform(other))
    
    def __rrshift__(self, other):
        if isinstance(other, Pipe):
            return Pipe(lambda iterable, *args, **kwargs: self.func(other.func(iterable, *args, **kwargs)))
        elif isinstance(other, Iterable) and not isinstance(other, (str, bytes)):
            return (self.func(i) for i in other) 
        else:
            return self.func(other)
    
    def __lshift__(self, other):
        if isinstance(other, Pipe):
            return Pipe(lambda iterable, *args, **kwargs: other.func(self.func(iterable, *args, **kwargs)))
        elif isinstance(other, Iterable) and not isinstance(other, (str, bytes)):
            return (self.func(i) for i in other) 
        else:
            return self.func(other)

    def __call__(self, *args, **kwargs):
        return Pipe(
            lambda iterable, *args2, **kwargs2: self.func(
                iterable, *args, *args2, **kwargs, **kwargs2
            )
        )
    
    @classmethod
    def pipe(cls, *funcs):
        funcs = [_transform(func) for func in funcs]
        def _compose(source):
            return functools.reduce(lambda obs, op: op(obs), funcs, source)
        return cls(_compose)
    
    @classmethod
    def compose(cls, *funcs):
        return cls.pipe(*reversed(funcs))

class Ops:
    @staticmethod
    @Pipe
    def map(it, *funcs):
        if not funcs:
            return it
        return it | Pipe(Ops._map_NONE(funcs[0])) | Ops.map(*funcs[1:])
    
    @staticmethod
    @Pipe
    def filter(it, *funcs):
        if not funcs:
            return it
        return it | Pipe(Ops._filter_NONE(funcs[0])) | Ops.filter(*funcs[1:])
    
    @staticmethod
    @Pipe
    def action(it, func=lambda x: x):
        if Ops._is_iterable(it):
            it = [i for i in it if i is not Ops.NONE]
            if all(i is not Ops.NONE for i in it):
                return it
            else:
                return Ops.action(it)
        else:
            return func(it) if it is not Ops.NONE else None
    
    @staticmethod
    @Pipe
    def flat_map(it, func):
        if it is not Ops.NONE:
            if Ops._is_iterable(it):
                for i in it:
                    if i is not Ops.NONE:
                        x = func(i)
                        if x is not Ops.NONE:
                            if Ops._is_iterable(x):
                                yield from x
                            else:
                                yield x
        else:
            x = func(it)
            if x is not Ops.NONE:
                if Ops._is_iterable(x):
                    yield from x
                else:
                    yield x
    
    @staticmethod
    @Pipe
    def fold(it, func, initial):
        acc = initial
        for item in it:
            if item is Ops.NONE:
                yield Ops.NONE
            else:
                acc = func(acc, item)
                yield acc
    
    @staticmethod
    @Pipe
    def count_by(it, key_func=None):
        g = {}
        if key_func is None:
            for item in it:
                if item is not Ops.NONE:
                    g[Ops._get_hash_key(item)] = g.get(Ops._get_hash_key(item), 0) + 1
        else:
            for item in it:
                if item is not Ops.NONE:
                    g[Ops._get_hash_key(key_func(item))] = g.get(Ops._get_hash_key(key_func(item)), 0) + 1
        for key, count in g.items():
            yield key, count
    
    @staticmethod
    @Pipe
    def count_by_distinct(it, key=None, *distinct_funcs):
        groups = {}
        for item in it:
            if item is Ops.NONE or item is None:
                continue
            group_key = key(item) if key else item
            group_key = Ops._get_hash_key(group_key)
            if group_key not in groups:
                groups[group_key] = []
            groups[group_key].append(item)
        
        for group_key, items in groups.items():
            func_counts = {}
            for func in distinct_funcs:
                results = set()
                for item in items:
                    if item is Ops.NONE or item is None:
                        continue
                    result = func(item)
                    if result is not Ops.NONE and result is not None:
                        results.add(result)
                func_counts[func.__name__] = len(results)
            yield (group_key, func_counts)
    
    @staticmethod
    @Pipe
    def grouper(it, size):
        batch = []
        for item in it:
            if item is Ops.NONE:
                continue
            batch.append(item)
            if len(batch) == size:
                yield batch
                batch = []
        if batch:
            yield batch
    
    @staticmethod
    @Pipe
    def group_by(it, key_func):
        groups = {}
        for item in it:
            if item is Ops.NONE:
                continue
            key = Ops._get_hash_key(key_func(item))
            if key not in groups:
                groups[key] = []
            groups[key].append(item)
        
        for key, group in groups.items():
            yield key, group
    
    @staticmethod
    @Pipe
    def reduce(it, func, initial=None):
        acc = initial
        first = True
        for item in it:
            if item is Ops.NONE:
                continue
            if first and initial is None:
                acc = item
                first = False
            else:
                acc = func(acc, item)
        return acc
    
    @staticmethod
    @Pipe
    def sort_by(it, key=None, reverse=False):
        filtered = [item for item in it if item is not Ops.NONE]
        return sorted(filtered, key=key, reverse=reverse)
    
    @staticmethod
    @Pipe
    def take(iterable, qte):
        if not qte:
            return
        for item in iterable:
            yield item
            qte -= 1
            if qte == 0:
                break
    
    @staticmethod
    @Pipe
    def tail(iterable, qte):
        return deque(iterable, maxlen=qte)
    
    @staticmethod
    @Pipe
    def skip(iterable, qte):
        for item in iterable:
            if qte == 0:
                yield item
            else:
                qte -= 1
    
    @staticmethod
    @Pipe
    def dedup(iterable, key=lambda x: x):
        seen = set()
        for item in iterable:
            dupkey = key(item)
            if dupkey not in seen:
                seen.add(dupkey)
                yield item
    
    @staticmethod
    @Pipe
    def uniq(iterable, key=lambda x: x):
        iterator = iter(iterable)
        try:
            prev = next(iterator)
        except StopIteration:
            return
        yield prev
        prevkey = key(prev)
        for item in iterator:
            itemkey = key(item)
            if itemkey != prevkey:
                yield item
            prevkey = itemkey
    
    @staticmethod
    @Pipe
    def enumerate(iterable, start=0):
        return enumerate(iterable, start)
    
    @staticmethod
    @Pipe
    def permutations(iterable, r=None):
        yield from itertools.permutations(iterable, r)
    
    @staticmethod
    @Pipe
    def tap(x, func=print):
        func(x)
        return x
    
    @staticmethod
    @Pipe
    def traverse(args):
        if isinstance(args, (str, bytes)):
            yield args
            return
        for arg in args:
            try:
                yield from arg | Ops.traverse
            except TypeError:
                yield arg
    
    @staticmethod
    @Pipe
    def tee(iterable):
        for item in iterable:
            sys.stdout.write(repr(item) + "\n")
            yield item
    
    @staticmethod
    @Pipe
    def select(iterable, selector):
        return map(selector, iterable)
    
    @staticmethod
    @Pipe
    def where(iterable, predicate):
        return (x for x in iterable if predicate(x))
    
    @staticmethod
    @Pipe
    def take_while(iterable, predicate):
        return itertools.takewhile(predicate, iterable)
    
    @staticmethod
    @Pipe
    def skip_while(iterable, predicate):
        return itertools.dropwhile(predicate, iterable)
    
    @staticmethod
    @Pipe
    def groupby(iterable, keyfunc):
        return itertools.groupby(sorted(iterable, key=keyfunc), keyfunc)
    
    @staticmethod
    @Pipe
    def sort(iterable, key=None, reverse=False):
        return sorted(iterable, key=key, reverse=reverse)
    
    @staticmethod
    @Pipe
    def reverse(iterable):
        return reversed(iterable)
    
    @staticmethod
    @Pipe
    def t(iterable, y):
        if hasattr(iterable, "__iter__") and not isinstance(iterable, str):
            return iterable + type(iterable)([y])
        return [iterable, y]
    
    @staticmethod
    @Pipe
    def transpose(iterable):
        return list(zip(*iterable))
    
    @staticmethod
    @Pipe
    def as_list(iterable):
        return [i for i in iterable if i is not Ops.NONE]
    
    @staticmethod
    @Pipe
    def batched(iterable, n):
        iterator = iter(iterable)
        while batch := tuple(itertools.islice(iterator, n)):
            yield batch
    
    @staticmethod
    @Pipe
    def chain(it):
        return itertools.chain.from_iterable(it)
    
    @staticmethod
    @Pipe
    def chain_with(it, *iterables):
        return itertools.chain(it, *iterables)
    
    @staticmethod
    @Pipe
    def islice(iterable, *args):
        return itertools.islice(iterable, *args)
    
    @staticmethod
    @Pipe
    def izip(*iterables):
        return zip(*iterables)
    
    @staticmethod
    @Pipe
    def as_list(it):
        return list(i for i in it if i is not Ops.NONE)
    
    @staticmethod
    @Pipe
    def tap(x, func=print):
        func(x)
        return x
    
    # 内部工具方法
    class _NONE:
        __slots__ = ()
        _instance = None
        
        def __new__(cls):
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance
        
        def __eq__(self, other):
            return other is Ops.NONE
        
        def __bool__(self):
            return False
        
        def __ne__(self, other):
            return not self.__eq__(other)
        
        def __repr__(self):
            return "NONE"
    
    NONE = _NONE()
    
    @staticmethod
    def _map_NONE(map_func):
        @wraps(map_func)
        def wrapper(x):
            if x is Ops.NONE:
                return Ops.NONE
            return map_func(x)
        return wrapper
    
    @staticmethod
    def _filter_NONE(filter_func):
        @wraps(filter_func)
        def wrapper(x):
            if x is Ops.NONE:
                return Ops.NONE
            return x if filter_func(x) else Ops.NONE
        return wrapper
    
    @staticmethod
    def _is_iterable(x):
        return isinstance(x, Iterable) and not isinstance(x, (str, bytes))
    
    @staticmethod
    def _get_hash_key(obj):
        if isinstance(obj, dict):
            return tuple(sorted(obj.items()))
        elif isinstance(obj, (list, tuple)):
            return tuple(obj)
        else:
            return obj



NONE = Ops.NONE


if __name__ == "__main__":
    as_list = Ops.as_list
    tap = Ops.tap
    NONE = Ops.NONE
    print([i for i in dir() if i[0] != "_"])
    m = Pipe.pipe(
        lambda x: x * 2,
        lambda x: x + 1,
        lambda x: x ** 2
    )
    n = Pipe.pipe(
        lambda x : (x,1)
    )
    
    print(9 >> m >> n)
    
    
    m >>= n
    print(range(10) >> m | as_list)
    
    print(range(10) | as_list)
    # n <<= m
    # print(9 >> n)
    print([1, 2, 3]  | as_list)
    

    @Ops.map
    def jisuan(x):
        return x * 2
    
    @Ops.map
    def jisuan1(x):
        
        return x * 3
    

    # x = range(5) >> Ops.map(lambda x: x * 2, lambda x: x + 1, lambda x: x ** 2,lambda x: x +1  if x < 30 else NONE) | as_list  | tap()
    
    # y = range(10) >> jisuan | as_list 
    # y | tap()
    # range(10) >> jisuan | Ops.action() | tap()
    # print(type(y),isinstance(y,Iterable),isinstance(y,Pipe),isinstance(y,staticmethod))
    # print(type(jisuan),isinstance(jisuan,Iterable),isinstance(jisuan,Pipe),isinstance(jisuan,staticmethod))
    
    x = range(10) >> jisuan >>  jisuan1 | as_list | tap
    print(x)
    
    jisuan >>= lambda x: x * 3
    range(10) >> jisuan | as_list | tap
    
    
        
        
        # 转换算子示例
    @Ops.flat_map
    def split_words(s):
        return s.split()

    @Ops.fold
    def sum_fold(acc, x):
        return acc + x

    # 行动算子示例
    @Ops.reduce
    def product(acc, x):
        return acc * x

    @Ops.sort_by
    def sort_func(item):
        return item[0]

    # 使用管道
    data = ["hello world", "python pipes", 'None', "NONE test"]

    # 转换算子链
    result = (
        data 
        | split_words() # 展平为单词
        | sum_fold('')      # 累积求和
        | as_list                     # 转为列表
    )
    print(result)  # [0, 'hello', 'hello world', ...]

    # 行动算子链
    reduced = (
        [2, 3, NONE, 4]
        | product(1)  # 计算乘积 (过滤None)
    )
    print(reduced)  # 24 (2 * 3 * 4)

    sorted_data = (
        [("b", 2), ("a", 1), 'None', ("c", 3)]
        | sort_func # 按数字排序
    )
    print(sorted_data)  # [('a', 1), ('b', 2), ('c', 3)]
    
    
    data = [(1,2),(1,3),(2,3),(2,4),(3,4),(3,5)]
    
    data | Ops.count_by(lambda x:x[0]) | tap() | as_list | tap()
    
    data | Ops.count_by_distinct(lambda x:x[0], lambda x:x[1])  | as_list | tap()
    
    data >> Ops.map(lambda x:x[1]) | Ops.action | tap
    data | Ops.map(lambda x:x[1]) | Ops.action | tap
    
