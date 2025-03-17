import traceback

from django.apps import AppConfig
from django.core.cache import cache
from loguru import logger


class CorkiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'corki'

    def ready(self):
        """
        应用准备就绪时调用的方法
        这里可以执行一些初始化操作，比如预热 Redis 连接池
        """
        # 预热 Redis 连接池
        self.warm_up_redis()

    def warm_up_redis(self):
        """
        预热 Redis 连接池的方法
        通过执行一个简单的缓存操作来初始化连接
        """
        try:
            # 执行一个简单的缓存操作来预热连接
            cache.set('redis_warmup_key', 'warmup_value', 10)
            warmup_value = cache.get('redis_warmup_key')

            if warmup_value == 'warmup_value':
                logger.info("Redis 连接已成功预热")
            else:
                logger.info("Redis 连接预热可能失败")

        except:
            logger.info(f"Redis 连接预热失败: {traceback.format_exc()}")
