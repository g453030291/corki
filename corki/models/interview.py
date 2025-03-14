from django.db import models
from pytz import timezone
from rest_framework import serializers, fields


class InterviewRecord(models.Model):
    id = models.AutoField(primary_key=True)
    user_id = models.IntegerField(default=0, null=False, help_text='用户id')
    cv_id = models.IntegerField(default=0, null=False, help_text='简历id')
    jd_id = models.IntegerField(default=0, null=False, help_text='职位id')
    jd_title = models.CharField(max_length=56, default='', null=False, help_text='职位名称')
    average_score = models.IntegerField(default=0, null=False, help_text='最后平均分')
    project_exp_score = models.IntegerField(default=0, null=False, help_text='项目经验得分')
    communication_score = models.IntegerField(default=0, null=False, help_text='沟通表达得分')
    professional_score = models.IntegerField(default=0, null=False, help_text='专业能力得分')
    logic_score = models.IntegerField(default=0, null=False, help_text='逻辑能力得分')
    teamwork_score = models.IntegerField(default=0, null=False, help_text='团队协作得分')
    learning_score = models.IntegerField(default=0, null=False, help_text='学习能力得分')
    proj_comm_suggest = models.JSONField(null=True, help_text='项目经验和沟通表达建议 (JSON格式)')
    teamwork_learn_suggest = models.JSONField(null=True, help_text='团队协作和学习能力建议 (JSON格式)')
    created_at = models.DateTimeField(auto_now_add=True, null=False, help_text='创建时间')
    creator_id = models.IntegerField(default=0, null=False, help_text='创建人 ID')
    creator_name = models.CharField(max_length=255, default='', null=False, help_text='创建账户名')
    updated_at = models.DateTimeField(auto_now=True, null=False, help_text='更新时间')
    updater_id = models.IntegerField(default=0, null=False, help_text='更新人 ID')
    updater_name = models.CharField(max_length=255, default='', null=False, help_text='更新账户名')
    deleted = models.IntegerField(default=0, null=False, help_text='删除标识:0=未删除,1=已删除')

    class Meta:
        managed = False
        db_table = 'interview_records'
        verbose_name = '面试记录'
        verbose_name_plural = '面试记录'

    @staticmethod
    def get_serializer(field_names=None):
        class InterviewRecordSerializer(serializers.ModelSerializer):
            created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", default_timezone=timezone('Asia/Shanghai'))
            # updated_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S", default_timezone=timezone('Asia/Shanghai'))

            class Meta:
                model = InterviewRecord
                fields = field_names if field_names is not None else '__all__'

        return InterviewRecordSerializer

class InterviewQuestion(models.Model):
    id = models.AutoField(primary_key=True)
    interview_id = models.IntegerField(default=0, null=False, help_text='面试 id')
    question_status = models.IntegerField(default=0, null=False, help_text='问答状态:0=未回答,1=已回答')
    question_type = models.IntegerField(default=0, null=False, help_text='问题类型:0=一级,1=二级,2=三级')
    question_closely_status = models.IntegerField(default=0, null=False, help_text='是否生成了追问:0=未生成,1=已生成')
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
    deleted = models.IntegerField(default=0, null=False, help_text='删除标识:0=未删除,1=已删除')

    class Meta:
        managed = False
        db_table = 'interview_questions'
        verbose_name = '面试问题记录'
        verbose_name_plural = '面试问题记录'
