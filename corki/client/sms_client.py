# import json
# import os
#
# import django
#
# os.environ['DJANGO_SETTINGS_MODULE'] = 'corki.settings'
# django.setup()
#
# from loguru import logger
# from volcengine.sms.SmsService import SmsService
#
# sms_service = SmsService()
# sms_service.set_ak(os.getenv('VOLCENGINE_ACCESS_KEY_ID'))
# sms_service.set_sk(os.getenv('VOLCENGINE_SECRET_ACCESS_KEY'))
#
# def send_code(phone, code):
#     body = {
#         "SmsAccount": os.getenv('VOLCENGINE_SMS_ACCOUNT_ID'),
#         "Sign": os.getenv('VOLCENGINE_SMS_SIGN_NAME'),
#         "TemplateID": os.getenv('VOLCENGINE_SMS_TEMPLATE_ID'),
#         "TemplateParam": f'{{"code": "{code}"}}',
#         "PhoneNumbers": phone,
#         "Tag": "tag",
#     }
#
#     body = json.dumps(body)
#     resp = sms_service.send_sms(body)
#     logger.info(f"send sms resp: {resp}")
#
# if __name__ == '__main__':
#     phone = ''
#     code = '1234'
#     send_code(phone, code)
