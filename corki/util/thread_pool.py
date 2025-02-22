from concurrent.futures import ThreadPoolExecutor

global_thread_pool = ThreadPoolExecutor(max_workers=20)

def submit_task(fn, *args, **kwargs):
    """
    提交任务到全局线程池
    :param fn: 要执行的函数
    :param args: 函数的位置参数
    :param kwargs: 函数的关键字参数
    :return: Future 对象
    """
    return global_thread_pool.submit(fn, *args, **kwargs)
