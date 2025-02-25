from django.db import models

class InterviewRecord(models.Model):
    id = models.AutoField(primary_key=True)
    user_id = models.IntegerField(default=0, null=False, help_text='用户id')
    cv_id = models.IntegerField(default=0, null=False, help_text='简历id')
    jd_id = models.IntegerField(default=0, null=False, help_text='职位id')
    created_at = models.DateTimeField(auto_now_add=True, null=False, help_text='创建时间')
    creator_id = models.IntegerField(default=0, null=False, help_text='创建人 ID')
    creator_name = models.CharField(max_length=255, default='', null=False, help_text='创建账户名')
    updated_at = models.DateTimeField(auto_now=True, null=False, help_text='更新时间')
    updater_id = models.IntegerField(default=0, null=False, help_text='更新人 ID')
    updater_name = models.CharField(max_length=255, default='', null=False, help_text='更新账户名')
    deleted = models.BooleanField(default=False, null=False, help_text='删除标识:0=未删除,1=已删除')

    class Meta:
        managed = False
        db_table = 'interview_records'
        verbose_name = '面试记录'
        verbose_name_plural = '面试记录'

class InterviewQuestion(models.Model):
    id = models.AutoField(primary_key=True)
    interview_id = models.IntegerField(default=0, null=False, help_text='面试 id')
    question_status = models.IntegerField(default=0, null=False, help_text='问答状态:0=未回答,1=已回答')
    question_type = models.IntegerField(default=0, null=False, help_text='问题类型:0=一级,1=二级,2=三级')
    parent_question_id = models.IntegerField(default=0, null=False, help_text='父级问题 id')
    module = models.CharField(max_length=56, default='', null=False, help_text='问题类型')
    question_content = models.CharField(max_length=128, default='', null=False, help_text='问题内容')
    question_url = models.CharField(max_length=128, default='', null=False, help_text='问题语音 url')
    answer_content = models.TextField(help_text='回答内容')
    created_at = models.DateTimeField(auto_now_add=True, null=False, help_text='创建时间')
    creator_id = models.IntegerField(default=0, null=False, help_text='创建人 ID')
    creator_name = models.CharField(max_length=255, default='', null=False, help_text='创建账户名')
    updated_at = models.DateTimeField(auto_now=True, null=False, help_text='更新时间')
    updater_id = models.IntegerField(default=0, null=False, help_text='更新人 ID')
    updater_name = models.CharField(max_length=255, default='', null=False, help_text='更新账户名')
    deleted = models.BooleanField(default=False, null=False, help_text='删除标识:0=未删除,1=已删除')

    class Meta:
        managed = False
        db_table = 'interview_questions'
        verbose_name = '面试问题记录'
        verbose_name_plural = '面试问题记录'
