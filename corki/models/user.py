from django.db import models

class CUser(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, default='', null=False, help_text='用户名')
    phone = models.CharField(max_length=20, default='', null=False, help_text='手机号')
    email = models.CharField(max_length=255, default='', null=False, help_text='邮箱')
    available_seconds = models.IntegerField(default=0, null=False, help_text='剩余用时,秒')
    created_at = models.DateTimeField(auto_now_add=True, null=False, help_text='创建时间')
    creator_id = models.IntegerField(default=0, null=False, help_text='创建人 ID')
    creator_name = models.CharField(max_length=255, default='', null=False, help_text='创建账户名')
    updated_at = models.DateTimeField(auto_now=True, null=False, help_text='更新时间')
    updater_id = models.IntegerField(default=0, null=False, help_text='更新人 ID')
    updater_name = models.CharField(max_length=255, default='', null=False, help_text='更新账户名')
    deleted = models.BooleanField(default=False, null=False, help_text='删除标识:0=未删除,1=已删除')

    class Meta:
        managed = False
        db_table = 'c_users'
