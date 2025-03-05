import time

def calculate_remaining_time(available_seconds, start_timestamp):
    """
    计算是否还有可用时长,用传入的 start_timestamp 和当前时间戳对比.不能返回负数.如果已经超过,就返回 0
    :param available_seconds:
    :param start_timestamp:
    :return:
    """
    current_timestamp = int(time.time())
    remaining_seconds = available_seconds - (current_timestamp - start_timestamp)
    return max(remaining_seconds, 0)
