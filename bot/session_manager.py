from common.expired_dict import ExpiredDict
from common.log import logger
from config import conf
import random


class Session(object):
    def __init__(self, session_id, system_prompt=None):
        self.session_id = session_id
        self.messages = []
        # 添加以下用于推荐食物和今日运势
        self.food_list = ["肉臊蒸蛋", "凉拌黄瓜", "皮蛋瘦肉粥", "红烧狮子头", "跷脚牛肉", "串串香", "牛肉面", "凉皮", "擀面皮", "臊子面", "油泼面", "炸酱面", "铜锅涮肉", "包子", "馄饨", "大盘鸡", "东北铁锅炖", "柴火鸡", "肉夹馍", "香菇滑鸡饭", "宫保鸡丁", "麻婆豆腐", "鱼香肉丝", "红烧肉", "回锅肉", "酱爆茄子", "糖醋排骨", "清蒸石斑鱼", "西红柿炒鸡蛋", "麻辣小龙虾", "辣子鸡", "蒜蓉蒸虾", "东坡肉", "烧茄子", "水煮牛肉", "酸菜鱼", "手抓羊肉","叉烧", "锅包肉", "饺子", "北京烤鸭", "爆炒花蛤", "剁椒鱼头", "香辣蟹","炒年糕", "干锅花菜", "爆炒大虾", "炒河粉", "炒面", "烤鱼", "火锅", "寿司", "烧烤", "炸串", "意大利面", "披萨", "KFC", "笔记本电脑", "群友", "考研真题"]
        if system_prompt is None:
            self.system_prompt = f"{conf().get('character_desc','')}\n如果有人问你运势，回答：财运{random.randint(0, 100)}，桃花运{random.randint(0, 100)}，事业运{random.randint(0, 100)}"
        else:
            self.system_prompt = system_prompt

    def get_random_food(self):
        return random.choice(self.food_list)


    # 重置会话
    def reset(self):
        system_item = {"role": "system", "content": self.system_prompt}
        self.messages = [system_item]

    def set_system_prompt(self, system_prompt):
        self.system_prompt = system_prompt
        self.reset()

    def add_query(self, query):
        user_item = {"role": "user", "content": query}
        self.messages.append(user_item)
        food_key_words = [
            "吃什么", "换一个", "不喜欢吃", "再来一个",
            "我不想要这个", "能不能换个", "换个别的",
            "想吃点别的", "不喜欢，换一个", "推荐别的"
        ]
        if any(keyword in query for keyword in food_key_words):
            self.add_reply(self.get_random_food())


    def add_reply(self, reply):
        assistant_item = {"role": "assistant", "content": reply}
        self.messages.append(assistant_item)

    def discard_exceeding(self, max_tokens=None, cur_tokens=None):
        raise NotImplementedError

    def calc_tokens(self):
        raise NotImplementedError


class SessionManager(object):
    def __init__(self, sessioncls, **session_args):
        if conf().get("expires_in_seconds"):
            sessions = ExpiredDict(conf().get("expires_in_seconds"))
        else:
            sessions = dict()
        self.sessions = sessions
        self.sessioncls = sessioncls
        self.session_args = session_args

    def build_session(self, session_id, system_prompt=None):
        """
        如果session_id不在sessions中，创建一个新的session并添加到sessions中
        如果system_prompt不会空，会更新session的system_prompt并重置session
        """
        if session_id is None:
            return self.sessioncls(session_id, system_prompt, **self.session_args)

        if session_id not in self.sessions:
            self.sessions[session_id] = self.sessioncls(session_id, system_prompt, **self.session_args)
        elif system_prompt is not None:  # 如果有新的system_prompt，更新并重置session
            self.sessions[session_id].set_system_prompt(system_prompt)
        session = self.sessions[session_id]
        return session

    def session_query(self, query, session_id):
        session = self.build_session(session_id)
        session.add_query(query)
        try:
            max_tokens = conf().get("conversation_max_tokens", 1000)
            total_tokens = session.discard_exceeding(max_tokens, None)
            logger.debug("prompt tokens used={}".format(total_tokens))
        except Exception as e:
            logger.warning("Exception when counting tokens precisely for prompt: {}".format(str(e)))
        return session

    def session_reply(self, reply, session_id, total_tokens=None):
        session = self.build_session(session_id)
        session.add_reply(reply)
        try:
            max_tokens = conf().get("conversation_max_tokens", 1000)
            tokens_cnt = session.discard_exceeding(max_tokens, total_tokens)
            logger.debug("raw total_tokens={}, savesession tokens={}".format(total_tokens, tokens_cnt))
        except Exception as e:
            logger.warning("Exception when counting tokens precisely for session: {}".format(str(e)))
        return session

    def clear_session(self, session_id):
        if session_id in self.sessions:
            del self.sessions[session_id]

    def clear_all_session(self):
        self.sessions.clear()
