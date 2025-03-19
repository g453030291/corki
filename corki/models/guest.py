from django.db import models

class GuestCodeRecords(models.Model):
    id = models.AutoField(primary_key=True)
    ip_address = models.CharField(max_length=64, default='', null=False, help_text='IP 地址')
    guest_code = models.CharField(max_length=256, default='', null=False, help_text='访客码')
    created_at = models.DateTimeField(auto_now_add=True, null=False, help_text='创建时间')
    creator_id = models.IntegerField(default=0, null=False, help_text='创建人 ID')
    creator_name = models.CharField(max_length=255, default='', null=False, help_text='创建账户名')
    updated_at = models.DateTimeField(auto_now=True, null=False, help_text='更新时间')
    updater_id = models.IntegerField(default=0, null=False, help_text='更新人 ID')
    updater_name = models.CharField(max_length=255, default='', null=False, help_text='更新账户名')
    deleted = models.BooleanField(default=False, null=False, help_text='删除标识:0=未删除,1=已删除')
    deleted_at = models.DateTimeField(null=True, help_text='删除时间')

    class Meta:
        managed = False
        db_table = 'guest_code_records'
        verbose_name = '访客码记录表'
        verbose_name_plural = '访客码记录表'
