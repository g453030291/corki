import io
import json
import os
import uuid
from concurrent.futures import wait

import django
from django.db import connection
from json_repair import json_repair
from loguru import logger

from corki.client import doubao_client, volcengine_client, oss_client
from corki.client.oss_client import OSSClient
from corki.models.interview import InterviewRecord, InterviewQuestion
from corki.models.prompts import PromptsManage
from corki.util.common_util import timeit
from corki.util.thread_pool import submit_task

os.environ['DJANGO_SETTINGS_MODULE'] = 'corki.settings'
django.setup()

from django.core.cache import cache

test_cv = """|  | 名:  |  |  | 年 龄: | 31 |  | 电话:  |
| --- | --- | --- | --- | --- | --- | --- | --- |
|  | 箱: |  |  | 工作经验: | 8 年 |  | 现住城市: 上海闵行区 |
|  | 从事职业: | java 开发 |  | 期望月薪: 面谈 |  |  |  |
|  | 学校名称: | 上海金融学院 |  | 就读时间: | 2010.09-2014.07 |  |  |
| 公司名称: | 哈啰出行 |  |  | 职位名称: | 资深开发 | 在职时间: | 2019.9-至今 |
| 主要负责: | 物联网系统 |  |  |  |  |  |  |
| 功能: | 全国设备的管理, | 设备创建, 管理, | 任务下发, | ota升级等。 |  |  |  |
| 公司名称: | 同程旅游 |  |  | 职位名称: | 资深开发 | 在职时间: | 2019.06-2019.9 |
| 主要负责: | 爱购宝系统, | cps 系统, |  |  |  |  |  |
| 功能: | 旅游保险业务 |  |  |  |  |  |  |
| 公司名称: 主要负责: | 日 日煮 订单系统 |  |  | 职位名称: | java 高级开发 | 在职时间: | 2017.07-2019.06 |
| 功能: | 全国订单管理, 退款, | 售后。 |  |  |  |  |  |
| 公司名称: | 中国亚信 |  |  | 职位名称: | java 开发 | 在职时间: | 2014.03-2017.07 |
| 主要负责: | 中国电信合作伙伴结算系统 |  |  |  |  |  |  |
| 功能: | 全国第三方电商平台, | 新用户推荐, | 返佣金。 |  |  |  |  |

熟练掌握 JAVA 面向对象编程语言, 有良好的编码习惯,多线程,JVM , 负责过千万级的项目开发 熟练掌握 mybatis ,Spring boot ,pringmvc,Dubbo 微服务 RPC 熟练掌握 Tomcat, weblogic 服务器, SVN, git 管理工具; 数据库: Oracle, MySQL, 有高并发, 负载均衡相关经验 熟悉应用容器, 服务框架 、消息中间件 、数据中间件 、熟悉缓存技术 redis, 分布式技术, 消息队列 MQ 对物联网平台, 电商有多年开发经验

## 项目名称: 哈**啰**出行物联网平台

项目时间: 2020.9 月 -今 项目描述: 对哈啰千万级的设备进行物联网系统的维护 项目框架: spring boot, 缓存: redis, 数据库 mysql, 配置中心:apollo ,注册中心 zokeerper, MQ: kafka, grpc框架, es 时序 hbase 职责: 项目开发, 模块设计, 参与需求调研 、项目可行性分析 、技术可行性分析

# 项目名称: 哈**啰**出行 资产管理系统

项目时间: 2020.1 月 -2020.6 月 项目描述: 负责全国助力车电池的充拉换功能, 进行城市间的助力车电池调拨, 维保, 城市间的电池借用领 用 项目框架: spring boot, 缓存: redis, 数据库 mysql, 配置中心:apollo ,注册中心 zokeerper, MQ: kafka, grpc框架 职责: 项目开发, 模块设计, 参与需求调研 、项目可行性分析 、技术可行性分析

#### 项目名称 : 同程旅游 爱购宝系统

项目时间: 2019.6 月 -2019.9 月 项目描述: 爱旅宝平台加爱购宝管理平台, 给线下旅行社定制旅游保险产品 。旅行 社通过爱旅宝平台根据旅游人员身份证进行投保, 生成保单, 可以退保, 申请理赔 。爱 购宝平台核查保单信息, 数据统计 项目框架: spring boot, 缓存: redis, 数据库 mysql 职责: 项目开发, 模块设计, 参与需求调研 、项目可行性分析 、技术可行性分析 和需求分析 。

### 项目名称: 日日煮电商系统订单

项目时间: 2018.3 月 -2019. 1 月项目描述: 日 日煮电商系统 (类似淘宝) , 用户下单买东西, 生成订单, 发货, 售后 项目框架: spring boot, 缓存: redis, rpc: dubbo, 数据库 mysql, 配置中心:apollo ,注册中心 zokeerper, MQ: rabbitMQ 职责: 项目开发, 模块设计, 参与需求调研 、项目可行性分析 、技术可行 性分析 和需求分析 。

用户下单, 通过购物车系统 RPC 传送给订单, 订单通过类似雪花算法, 生成单号, redis 幂等校验, 减库存 , 插入数据

库 生成订单, 供应商做发货操作, 用户根据 收货产品, 做收货退货操作。

#### 项目名称: 中国电信合作伙伴结算系统

项目时间: 2015 11 月 17 日- 2018 1 月 12 日 项目描述: 中国电信合作伙伴结算系统, 清算信息 开发环境与技术: 项目描述: 结算系统, 用户费用结算汇总 职责: 项目开发, 模块设计, 参与需求调研 、项目可行性分析 、技术可行性分析和需求分析
"""

test_jd = """资深全栈工程师职位详情
基本信息
发布人：王先生
所在公司：北京字节跳动
职位：研发负责人
活跃状态：2 月内活跃
职位描述
在 LLM 浪潮的背景下，我们正面临着一场激烈的技术变革。我们正寻求突破，希望在工程级别的代码生成以及迭代的开发模式领域中做出优秀的产品。具体职责如下：
探索并创造基于 LLM 的工程级代码生成服务和产品，助力开发者迎接更高效的提效体验。
关注 AI 领域的最新动态和趋势，结合开发者的实际需求，为我们提供高性能、适应性强的技术解决方案。
对产品的稳定性和性能极致的追求，深入理解并致力于优化和重构，确保系统高效、稳定运作。
职位要求
前端 or 后端至少精通一个方向，对另外的方向略懂。
前端开发要求：
熟悉 HTML、CSS、JavaScript 等 Web 前端技术。
有 Vue/React 等现代前端框架的使用经验。
理解 Node.js、Webpack 等前端工程化工具。
掌握 HTTP 协议、浏览器原理、性能优化等 Web 前端核心知识。
后端开发要求：对 Python、Java 等相关技术有一定掌握（可查看更多具体要求） 。
相关技能
掌握 Django/Flask、JavaScript、Vue、Node.js、React 等相关技术。
具有计算机相关专业背景，拥有前端开发经验、全栈项目经验，了解低代码平台。
沟通方式
立即沟通"""

system_prompt_content = PromptsManage.objects.get(id=1).prompts_content
follow_up_prompt = PromptsManage.objects.get(id=2).prompts_content

def completions_by_key(key, system_prompts, user_prompts="和我打个招呼吧"):
    """
    根据对话key获取缓存的对话历史，请求LLM API并返回响应

    Args:
        key (str): 对话缓存的唯一标识
        system_prompts (str): 系统提示语
        user_prompts (str, optional): 用户输入的提示语. Defaults to "和我打个招呼吧"

    Returns:
        str: LLM的响应内容
    """
    # 获取缓存的对话历史
    messages = cache.get(key)

    if messages:
        # 如果有历史对话记录，追加新的用户输入
        messages.append({"role": "user", "content": user_prompts})
    else:
        # 如果没有历史对话记录，创建新的对话
        messages = [
            {"role": "system", "content": system_prompts},
            {"role": "user", "content": user_prompts}
        ]

    # 请求LLM API
    completion_response = doubao_client.completions(
        system_prompts=None,
        user_prompts=None,
        messages=messages
    )
    logger.info(f"LLM response: {completion_response}")

    # 将AI响应添加到对话历史
    messages.append({"role": "assistant", "content": completion_response})

    # 更新缓存
    cache.set(key, messages, 60 * 60 * 24)  # 缓存24小时

    return completion_response

def conversation_init(cv, jd, cv_id, jd_id, jd_title, user):
    oss_client = OSSClient()
    # 1.获取当前初始对话的CV/JD
    completion_response = doubao_client.completions(
        system_prompts=system_prompt_content,
        user_prompts=f"user_profile:\n{cv}\n,job_information:\n{jd}"
    )
    interview_record = InterviewRecord.objects.create(user_id=user.id, cv_id=cv_id, jd_id=jd_id, jd_title=jd_title, deleted=1)
    # 2.调用LLM API生成问题
    completion_json = json_repair.loads(completion_response.replace("```", "").replace("json", ""))
    question_list = []
    for question in completion_json['questions']:
        question = InterviewQuestion.objects.create(interview_id=interview_record.id, question_content=question['question'], module=question['module'])
        question_list.append(question)
    # 3.调用接口生成语音并上传获取 url
    futures = [submit_task(process_audio, question_entity, oss_client) for question_entity in question_list]
    wait(futures)
    results = [future.result() for future in futures]
    logger.info(f"results: {results}")
    return {'interview_record_id': interview_record.id}

def follow_up_questions(question, answer):
    completion_response = doubao_client.completions(
        system_prompts=follow_up_prompt,
        user_prompts=f"question:\n{question}\n,answer:\n{answer}"
    )
    decoded_object = json_repair.loads(completion_response.replace("```", "").replace("json", ""))
    # completion_json = json.loads(decoded_object)
    return decoded_object

def process_audio(interview_question, oss_client):
    """
    调用接口生成语音并上传获取 url
    :param interview_question:
    :return:
    """
    audio_binary = volcengine_client.tts(interview_question.question_content)
    audio_stream = io.BytesIO(audio_binary)
    # base64转为音频二进制,并上传到OSS
    url = oss_client.put_object(f"{uuid.uuid4().hex}.mp3", audio_stream)
    InterviewQuestion.objects.filter(id=interview_question.id).update(question_url=url)
    return f'q_id: {interview_question.id}, url: {url}'

@timeit
def scoring_and_suggestion(interview_id):
    """
    评分和建议
    :param interview_id: 面试记录id
    :return:
    """
    modules = [
        'project_practice',
        'technical_ability',
        'behavioral_pattern',
        'proj_comm_suggest',
        'teamwork_learn_suggest'
    ]
    futures = [submit_task(process_interview_module, interview_id, module) for module in modules]
    wait(futures)
    with connection.cursor() as cursor:
        cursor.execute("""
            UPDATE interview_records
            SET average_score = (
                project_exp_score + communication_score + professional_score + logic_score + teamwork_score + learning_score
            ) / 6, deleted = 0
            WHERE id = %s
        """, [interview_id])


def process_interview_module(interview_id, interview_module):
    """
    处理单个面试模块
    :param interview_id: 面试记录id
    :param interview_module: 模块名称
    """
    # 定义每个模块的参数
    module_params = {
        'project_practice': {'prompt_id': 3, 'filter_by_module': True},
        'technical_ability': {'prompt_id': 4, 'filter_by_module': True},
        'behavioral_pattern': {'prompt_id': 5, 'filter_by_module': True},
        'proj_comm_suggest': {'prompt_id': 6, 'filter_by_module': False},
        'teamwork_learn_suggest': {'prompt_id': 7, 'filter_by_module': False}
    }

    if interview_module not in module_params:
        logger.info(f"interview_module error:{interview_module}")
        return

    # 获取参数
    prompt_id = module_params[interview_module]['prompt_id']
    filter_by_module = module_params[interview_module]['filter_by_module']

    # 获取prompts
    prompts_manage = PromptsManage.objects.get(id=prompt_id)

    # 获取问题列表
    if filter_by_module:
        question_list = InterviewQuestion.objects.filter(interview_id=interview_id,
                                                         module=interview_module).all()
    else:
        question_list = InterviewQuestion.objects.filter(interview_id=interview_id).all()

    # 拼接内容
    content = "\n".join([f"问题：{q.question_content}\n回答：{q.answer_content}" for q in question_list])

    # 调用AI接口
    completion_response = doubao_client.completions(
        system_prompts=prompts_manage.prompts_content,
        user_prompts=content
    )
    # ,
    # model = 'ep-20250203164051-95ppp'

    # 解析返回结果
    decoded_object = json_repair.loads(completion_response)

    # 根据不同模块更新不同的字段
    if interview_module == 'project_practice':
        InterviewRecord.objects.filter(id=interview_id).update(
            project_exp_score=decoded_object['score']['project_exp_score'],
            communication_score=decoded_object['score']['communication_score']
        )
    elif interview_module == 'technical_ability':
        InterviewRecord.objects.filter(id=interview_id).update(
            professional_score=decoded_object['score']['professional_score'],
            logic_score=decoded_object['score']['logic_score']
        )
    elif interview_module == 'behavioral_pattern':
        InterviewRecord.objects.filter(id=interview_id).update(
            teamwork_score=decoded_object['score']['teamwork_score'],
            learning_score=decoded_object['score']['learning_score']
        )
    elif interview_module == 'proj_comm_suggest':
        InterviewRecord.objects.filter(id=interview_id).update(
            proj_comm_suggest=decoded_object
        )
    elif interview_module == 'teamwork_learn_suggest':
        InterviewRecord.objects.filter(id=interview_id).update(
            teamwork_learn_suggest=decoded_object
        )


if __name__ == '__main__':
    scoring_and_suggestion(InterviewRecord(id=15))
    # sys_prompts, user_content = prompts_and_content(InterviewRecord(id=15), 'project_practice')
    # print(sys_prompts)
    # print('-----------')
    # print(user_content)
    # result = completions_by_key("key", "你是字节跳动开发的AI智能助手", "你好,豆包")
    # print(result)
    # conversation_init()
    # scoring_and_suggestion(None, 'project_exp_score', '', '')
    # follow_up_questions('在Spring Boot项目中，如何实现配置的动态更新与管理？', '不清楚,下一个问题')
