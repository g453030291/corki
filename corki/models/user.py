from django.db import models
from rest_framework import serializers

class CUser(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, default='', null=False, help_text='用户名')
    phone = models.CharField(max_length=20, default='', null=False, help_text='手机号', unique=True)
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
    cv_url = models.CharField(max_length=128, default='', null=False, help_text='简历地址')
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
            class Meta:
                model = UserCV
                fields = 'id', 'user_id', 'cv_url', 'created_at'
        return UserCVSerializer

class UserJD(models.Model):
    id = models.AutoField(primary_key=True)
    user_id = models.IntegerField(default=0, null=False, help_text='用户 ID')
    jd_url = models.CharField(max_length=128, default='', null=False, help_text='简历地址')
    jd_content = models.TextField(null=True, help_text='简历内容')
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
            class Meta:
                model = UserJD
                fields = 'id', 'user_id', 'jd_url', 'created_at'
        return UserJDSerializer
