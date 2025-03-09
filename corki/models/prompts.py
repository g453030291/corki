from django.db import models

class PromptsManage(models.Model):
    id = models.AutoField(primary_key=True)
    prompts_type = models.IntegerField(default=0, null=False, help_text='提示类型')
    prompts_content = models.TextField(null=False, help_text='提示内容')
    created_at = models.DateTimeField(auto_now_add=True, null=False, help_text='创建时间')
    creator_id = models.IntegerField(default=0, null=False, help_text='创建人 ID')
    creator_name = models.CharField(max_length=255, default='', null=False, help_text='创建账户名')
    updated_at = models.DateTimeField(auto_now=True, null=False, help_text='更新时间')
    updater_id = models.IntegerField(default=0, null=False, help_text='更新人 ID')
    updater_name = models.CharField(max_length=255, default='', null=False, help_text='更新账户名')
    deleted = models.IntegerField(default=0, null=False, help_text='删除标识:0=未删除,1=已删除')

    class Meta:
        managed = False
        db_table = 'prompts_manage'
        verbose_name = '系统提示词管理表'
        verbose_name_plural = '系统提示词管理表'
