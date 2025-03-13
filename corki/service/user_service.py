import os

import django
from loguru import logger

from corki.client.ali_client import AliClient

os.environ['DJANGO_SETTINGS_MODULE'] = 'corki.settings'
django.setup()
from corki.models.user import UserCV, UserJD


def analysis_cv_jd(user_cv: UserCV, user_jd: UserJD):
    """
    解析cv/jd
    :param user_jd: 职位
    :param user_cv: 简历
    :return:
    """

    if user_cv:
        url = user_cv.cv_url
        doc_result = AliClient.doc_mind(
            url=url,
            file_name=os.path.basename(url)
        )
        UserCV.objects.filter(id=user_cv.id).update(cv_content=doc_result)
        logger.info(f"cv解析完成:id={user_cv.id}")
    elif user_jd:
        url = user_jd.jd_url
        ocr_result = AliClient.ocr(url)
        UserJD.objects.filter(id=user_jd.id).update(jd_content=ocr_result)
        logger.info(f"jd解析完成:id={user_jd.id}")
    else:
        logger.info("cv/jd不存在")
        return None

if __name__ == '__main__':
    url = "https://corki-oss.oss-cn-beijing.aliyuncs.com/2025/02/22/176416b12bce49d98c7684442b604f60.mp3"
    print(os.path.basename(url))
