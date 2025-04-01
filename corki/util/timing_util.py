import time

from loguru import logger


def calculate_remaining_time(available_seconds, start_timestamp, current_ts=None):
    """
    计算是否还有可用时长,用传入的 start_timestamp 和当前时间戳对比.不能返回负数.如果已经超过,就返回 0
    :param available_seconds:
    :param start_timestamp:
    :param current_ts: 可选，当前时间戳，如果不提供则使用当前系统时间
    :return:
    """
    if current_ts is None:
        current_ts = int(time.time())
    remaining_seconds = available_seconds - (current_ts - start_timestamp)
    logger.info(f"Available seconds: {available_seconds}, Start timestamp: {start_timestamp}, Current timestamp: {current_ts}, Remaining seconds: {remaining_seconds}")
    return max(remaining_seconds, 0)

def get_time_difference(start_timestamp, current_timestamp=None):
    """
    计算当前时间到 start_timestamp 的差值，秒数
    :param start_timestamp: 开始时间戳
    :param current_timestamp: 可选，当前时间戳，如果不提供则使用当前系统时间
    :return: 时间差（秒）
    """
    if current_timestamp is None:
        current_timestamp = int(time.time())
    time_difference = current_timestamp - start_timestamp
    logger.info(f"Start timestamp: {start_timestamp}, Current timestamp: {current_timestamp}, Time difference: {time_difference}")
    return time_difference
