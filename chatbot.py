import os
import logging
from openai import OpenAI, OpenAIError
from flask import session, current_app
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AIChat:
    def __init__(self):
        # 从环境变量获取API密钥，如果没有则使用默认值
        self.api_key = os.getenv('DEEPSEEK_API_KEY', "sk-4c0e05f2a6ac46ed80426276b1c255eb")
        try:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url="https://api.deepseek.com"
            )
            logger.info("AI Chat initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize AI Chat: {str(e)}")
            raise
        self.conversation_history = {}

    def _clean_history(self, user_id):
        """清理超过10条的历史记录"""
        if len(self.conversation_history[user_id]) > 10:
            self.conversation_history[user_id] = self.conversation_history[user_id][-10:]
            logger.info(f"Cleaned history for user {user_id}, now has {len(self.conversation_history[user_id])} messages")

    def get_response(self, user_id, message):
        """获取AI响应"""
        if not message or not user_id:
            logger.error("Missing required parameters")
            return "消息内容或用户ID不能为空"

        try:
            logger.info(f"Processing message from user {user_id}: {message[:50]}...")
            
            # 初始化或获取会话历史
            if user_id not in self.conversation_history:
                self.conversation_history[user_id] = []
                logger.info(f"Created new conversation history for user {user_id}")
            
            # 添加用户消息到历史记录
            self.conversation_history[user_id].append({
                "role": "user",
                "content": message,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # 清理历史记录
            self._clean_history(user_id)
            
            # 准备消息列表
            messages = [
                {
                    "role": "system", 
                    "content": "你是一个友好、专业的AI助手。请用简洁、准确的方式回答问题。始终使用中文回复。"
                }
            ]
            messages.extend([
                {"role": msg["role"], "content": msg["content"]} 
                for msg in self.conversation_history[user_id]
            ])
            
            # 调用AI API
            logger.info("Calling AI API...")
            try:
                response = self.client.chat.completions.create(
                    model="deepseek-chat",
                    messages=messages,
                    max_tokens=500,
                    temperature=0.7,
                    presence_penalty=0.6,
                    frequency_penalty=0.6
                )
                
                # 提取响应文本
                ai_message = response.choices[0].message.content
                if not ai_message:
                    raise ValueError("Empty response from AI")
                    
                logger.info(f"Got AI response: {ai_message[:50]}...")
                
                # 添加AI响应到历史记录
                self.conversation_history[user_id].append({
                    "role": "assistant",
                    "content": ai_message,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                return ai_message
                
            except OpenAIError as e:
                logger.error(f"OpenAI API error: {str(e)}", exc_info=True)
                error_message = str(e)
                if "rate_limit" in error_message.lower():
                    return "服务请求过于频繁，请稍后再试"
                elif "connection" in error_message.lower():
                    return "网络连接出现问题，请检查网络连接"
                else:
                    return f"AI服务出现错误：{error_message}"
            except Exception as e:
                logger.error(f"Unexpected error in API call: {str(e)}", exc_info=True)
                return "AI服务暂时不可用，请稍后再试"
            
        except Exception as e:
            logger.error(f"Error in get_response: {str(e)}", exc_info=True)
            return "系统处理出现错误，请稍后重试"

    def clear_history(self, user_id):
        """清除用户的对话历史"""
        try:
            if user_id in self.conversation_history:
                self.conversation_history.pop(user_id)
                logger.info(f"Cleared conversation history for user {user_id}")
                return True
            logger.info(f"No history found for user {user_id}")
            return False
        except Exception as e:
            logger.error(f"Error clearing history for user {user_id}: {str(e)}", exc_info=True)
            return False

# 创建全局实例
try:
    ai_chat = AIChat()
    logger.info("Global AI Chat instance created successfully")
except Exception as e:
    logger.error(f"Failed to create global AI Chat instance: {str(e)}")
    raise
