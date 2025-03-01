import os
from uuid import uuid4


import django
from loguru import logger

os.environ['DJANGO_SETTINGS_MODULE'] = 'corki.settings'
django.setup()
from corki.config.constant import TMP_PATH
from corki.models.user import UserCV, UserJD
from corki.util import file_util, pdf_util, ocr_util


def analysis_cv_jd(user_cv: UserCV, user_jd: UserJD):
    """
    解析cv/jd
    :param user_jd: 职位
    :param user_cv: 简历
    :return:
    """
    if user_cv:
        url = user_cv.cv_url
        path = TMP_PATH + os.path.basename(url)
        file_util.download_file(path, url)
        text = pdf_util.extract_text_from_pdf(path)
        UserCV.objects.filter(id=user_cv.id).update(cv_content=text)
        os.remove(path)
        logger.info(f"cv解析完成:id={user_cv.id}")
    elif user_jd:
        url = user_jd.jd_url
        path = TMP_PATH + os.path.basename(url)
        file_util.download_file(path, url)
        text = ocr_util.extract_text_from_image(path)
        UserJD.objects.filter(id=user_jd.id).update(jd_content=text)
        os.remove(path)
        logger.info(f"jd解析完成:id={user_jd.id}")
    else:
        logger.info("cv/jd不存在")
        return None

if __name__ == '__main__':
    url = "https://corki-oss.oss-cn-beijing.aliyuncs.com/2025/02/22/176416b12bce49d98c7684442b604f60.mp3"
    print(os.path.basename(url))
