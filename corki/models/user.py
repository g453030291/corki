from django.db import models
from pytz import timezone
from rest_framework import serializers

class CUser(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, default='', null=False, help_text='用户名')
    phone = models.CharField(max_length=20, default='', null=False, help_text='手机号', unique=True)
    guest_code = models.CharField(max_length=128, default='', null=False, help_text='匿名用户')
    email = models.CharField(max_length=255, default='', null=False, help_text='邮箱')
    available_seconds = models.IntegerField(default=0, null=False, help_text='剩余用时,秒')
    created_at = models.DateTimeField(auto_now_add=True, null=False, help_text='创建时间')
    creator_id = models.IntegerField(default=0, null=False, help_text='创建人 ID')
    creator_name = models.CharField(max_length=255, default='', null=False, help_text='创建账户名')
    updated_at = models.DateTimeField(auto_now=True, null=False, help_text='更新时间')
    updater_id = models.IntegerField(default=0, null=False, help_text='更新人 ID')
    updater_name = models.CharField(max_length=255, default='', null=False, help_text='更新账户名')
    deleted = models.IntegerField(default=0, null=False, help_text='删除标识:0=未删除,1=已删除')

    is_authenticated = True

    class Meta:
        managed = False
        db_table = 'c_users'

    @staticmethod
    def get_serializer():
        class CUserSerializer(serializers.ModelSerializer):
            class Meta:
                model = CUser
                fields = '__all__'
        return CUserSerializer

class UserCV(models.Model):
    id = models.AutoField(primary_key=True)
    user_id = models.IntegerField(default=0, null=False, help_text='用户 ID')
    guest_code = models.CharField(max_length=128, default='', null=False, help_text='匿名用户')
    default_status = models.IntegerField(default=0, null=False, help_text='默认状态:0=非默认,1=默认')
    cv_url = models.CharField(max_length=128, default='', null=False, help_text='简历地址')
    cv_name = models.CharField(max_length=56, default='', null=False, help_text='简历名称')
    cv_content = models.TextField(null=True, help_text='简历内容')
    created_at = models.DateTimeField(auto_now_add=True, null=False, help_text='创建时间')
    creator_id = models.IntegerField(default=0, null=False, help_text='创建人 ID')
    creator_name = models.CharField(max_length=255, default='', null=False, help_text='创建账户名')
    updated_at = models.DateTimeField(auto_now=True, null=False, help_text='更新时间')
    updater_id = models.IntegerField(default=0, null=False, help_text='更新人 ID')
    updater_name = models.CharField(max_length=255, default='', null=False, help_text='更新账户名')
    deleted = models.IntegerField(default=0, null=False, help_text='删除标识:0=未删除,1=已删除')

    class Meta:
        managed = False
        db_table = 'user_cv'
        verbose_name = '用户简历表'
        verbose_name_plural = '用户简历表'

    @staticmethod
    def get_serializer():
        class UserCVSerializer(serializers.ModelSerializer):
            created_at = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', default_timezone=timezone('Asia/Shanghai'))
            class Meta:
                model = UserCV
                fields = 'id', 'user_id', 'default_status', 'cv_name', 'cv_url', 'created_at'
        return UserCVSerializer

class UserJD(models.Model):
    id = models.AutoField(primary_key=True)
    user_id = models.IntegerField(default=0, null=False, help_text='用户 ID')
    guest_code = models.CharField(max_length=128, default='', null=False, help_text='匿名用户')
    default_status = models.IntegerField(default=0, null=False, help_text='默认状态:0=非默认,1=默认')
    jd_url = models.CharField(max_length=128, default='', null=False, help_text='职位链接地址')
    jd_title = models.CharField(max_length=255, default='', null=False, help_text='职位名称')
    jd_content = models.TextField(null=True, help_text='职位内容')
    created_at = models.DateTimeField(auto_now_add=True, null=False, help_text='创建时间')
    creator_id = models.IntegerField(default=0, null=False, help_text='创建人 ID')
    creator_name = models.CharField(max_length=255, default='', null=False, help_text='创建账户名')
    updated_at = models.DateTimeField(auto_now=True, null=False, help_text='更新时间')
    updater_id = models.IntegerField(default=0, null=False, help_text='更新人 ID')
    updater_name = models.CharField(max_length=255, default='', null=False, help_text='更新账户名')
    deleted = models.IntegerField(default=0, null=False, help_text='删除标识:0=未删除,1=已删除')

    class Meta:
        managed = False
        db_table = 'user_jd'
        verbose_name = '用户简历表'
        verbose_name_plural = '用户简历表'

    @staticmethod
    def get_serializer():
        class UserJDSerializer(serializers.ModelSerializer):
            created_at = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', default_timezone=timezone('Asia/Shanghai'))

            class Meta:
                model = UserJD
                fields = 'id', 'user_id', 'default_status', 'jd_title', 'jd_url', 'created_at'
        return UserJDSerializer
