import os

from corki.config.constant import TMP_PATH
from corki.util import file_util


# 生成一个图片压缩的工具类，要求如下
#图片尺寸
#图片长宽需要大于 15 像素，小于 8192 像素。
# 长宽比需要小于 50。
# 如需达到较好识别效果，建议长宽均大于 500px。
# 图片大小
# 图片二进制文件不能超过 10MB。
def is_valid_image(url: str) -> str:
    img_path = TMP_PATH + os.path.basename(url)
    # file_util.download_file(path, url)
    # """
    # 判断图片是否符合要求
    # :param image: 图片文件
    # :return: True or False
    # """
    # # 判断图片尺寸
    # if image.size[0] < 15 or image.size[1] < 15:
    #     return False
    # if image.size[0] > 8192 or image.size[1] > 8192:
    #     return False
    # if image.size[0] / image.size[1] > 50 or image.size[1] / image.size[0] > 50:
    #     return False
    #
    # # 判断图片大小
    # if len(image.tobytes()) > 10 * 1024 * 1024:
    #     return False
    #
    # return True

if __name__ == '__main__':
    print(os.path.basename('https://corki-oss.oss-cn-beijing.aliyuncs.com/2025/03/31/14f6e418e3f643799361eb807d75ead5.jpg'))
    