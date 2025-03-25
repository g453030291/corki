from django.core.cache import cache
from loguru import logger
import uuid
import time
from functools import wraps


class DistributedLock:
    """
    分布式锁的实现
    使用 Redis 作为底层存储，支持超时和锁持有者标识
    """

    def __init__(self, lock_key, timeout=60):
        """
        初始化分布式锁
        :param lock_key: 锁的唯一标识键
        :param timeout: 锁的超时时间(秒)，默认60秒
        """
        self.lock_key = f"distributed_lock:{lock_key}"
        self.timeout = timeout
        self.lock_id = str(uuid.uuid4())  # 锁的持有者标识

    def acquire(self, blocking=True, retry_interval=0.1, retry_times=None):
        """
        获取锁
        :param blocking: 是否阻塞等待
        :param retry_interval: 重试间隔时间(秒)
        :param retry_times: 重试次数，None表示一直重试直到超时
        :return: 是否成功获取锁
        """
        tries = 0
        while True:
            # 使用 setnx 命令确保原子性操作
            if cache.add(self.lock_key, self.lock_id, timeout=self.timeout):
                logger.debug(f"Successfully acquired lock: {self.lock_key} with id: {self.lock_id}")
                return True

            if not blocking:
                return False

            if retry_times is not None and tries >= retry_times:
                logger.warning(f"Failed to acquire lock: {self.lock_key} after {tries} attempts")
                return False

            tries += 1
            time.sleep(retry_interval)

    def release(self):
        """
        释放锁
        只有锁的持有者才能释放锁
        :return: 是否成功释放锁
        """
        try:
            # 确保只有锁的持有者才能释放锁
            current_lock_id = cache.get(self.lock_key)
            if current_lock_id != self.lock_id:
                logger.warning(
                    f"Cannot release lock: {self.lock_key}. "
                    f"Current lock id: {current_lock_id} != {self.lock_id}"
                )
                return False

            cache.delete(self.lock_key)
            logger.debug(f"Successfully released lock: {self.lock_key}")
            return True

        except Exception as e:
            logger.error(f"Failed to release lock: {self.lock_key}, error: {e}")
            return False

    def __enter__(self):
        """支持 with 语句"""
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """支持 with 语句"""
        self.release()


def with_distributed_lock(lock_key, timeout=60):
    """
    分布式锁装饰器
    :param lock_key: 锁的唯一标识键
    :param timeout: 锁的超时时间(秒)
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with DistributedLock(lock_key, timeout):
                return func(*args, **kwargs)

        return wrapper

    return decorator