from flask import session
from flask_socketio import emit
from models import User, Message, db, init_ai_assistant
from datetime import datetime
import json
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建AI聊天实例
from chatbot import AIChat
ai_chat = AIChat()

def init_socket_events(app, socketio):
    """初始化Socket.IO事件
    
    Args:
        app: Flask应用实例
        socketio: SocketIO实例
    """
    # 确保AI助手用户存在
    ai_assistant = init_ai_assistant(app)
    if not ai_assistant:
        logger.error("Failed to initialize AI assistant user")
        raise RuntimeError("Failed to initialize AI assistant user")

    @socketio.on('connect')
    def handle_connect():
        logger.info('用户尝试连接，session: %s', session)
        if 'user_id' in session:
            socketio.server.enter_room(session['user_id'])
            emit('connected', {'user_id': session['user_id']})
            logger.info('用户已连接: %s', session['user_id'])
        else:
            logger.warning('未登录用户尝试连接')
            emit('error', {'message': '请先登录后再聊天'})

    @socketio.on('disconnect')
    def handle_disconnect():
        if 'user_id' in session:
            socketio.server.leave_room(session['user_id'])
            logger.info('用户已断开连接: %s', session['user_id'])

    @socketio.on('send_message')
    def handle_message(data):
        logger.info('收到消息: %s', data)
        
        # 验证用户登录状态
        if 'user_id' not in session:
            logger.warning('未登录用户尝试发送消息')
            emit('error', {'message': '请先登录'})
            return
        
        # 验证消息数据
        try:
            content = data.get('content')
            message_type = data.get('type', 'text')
            recipient_id = data.get('recipient_id')
            
            if not content or not recipient_id:
                logger.warning('消息数据不完整: content=%s, recipient_id=%s', content, recipient_id)
                emit('error', {'message': '消息数据不完整'})
                return
            
            logger.info('消息内容验证通过，准备处理')
            
            # 获取AI助手用户
            ai_assistant = User.query.filter_by(username='AI助手').first()
            if not ai_assistant:
                logger.error('未找到AI助手用户')
                emit('error', {'message': '系统错误：AI助手未配置'})
                return
            
            logger.info('找到AI助手用户: %s', ai_assistant.id)
            
            # 创建并保存用户消息
            try:
                user_message = Message(
                    content=content,
                    message_type=message_type,
                    sender_id=session['user_id'],
                    recipient_id=ai_assistant.id,
                    status='sent',
                    timestamp=datetime.utcnow()
                )
                db.session.add(user_message)
                db.session.commit()
                logger.info('用户消息已保存')
                
                # 发送消息确认
                emit('message_sent', user_message.to_dict())
                
            except Exception as e:
                logger.error('保存用户消息失败: %s', str(e), exc_info=True)
                db.session.rollback()
                emit('error', {'message': '消息发送失败'})
                return
            
            # 获取AI响应
            try:
                ai_response = ai_chat.get_response(session['user_id'], content)
                if not ai_response:
                    raise ValueError("AI response is empty")
                    
                logger.info('获取到AI响应: %s', ai_response[:50])
                
                # 创建并保存AI响应消息
                ai_message = Message(
                    content=ai_response,
                    message_type='text',
                    sender_id=ai_assistant.id,
                    recipient_id=session['user_id'],
                    status='sent',
                    timestamp=datetime.utcnow()
                )
                db.session.add(ai_message)
                db.session.commit()
                logger.info('AI响应消息已保存')
                
                # 发送AI响应给用户
                emit('new_message', ai_message.to_dict(), room=session['user_id'])
                logger.info('AI响应已发送给用户')
                
            except Exception as e:
                logger.error('处理AI响应失败: %s', str(e), exc_info=True)
                db.session.rollback()
                emit('error', {'message': str(e) if str(e) else 'AI响应失败，请稍后重试'})
                return
                
        except Exception as e:
            logger.error('消息处理过程中发生错误: %s', str(e), exc_info=True)
            emit('error', {'message': '消息处理失败'})
            return

    @socketio.on('mark_read')
    def handle_mark_read(data):
        if 'user_id' not in session:
            logger.warning('未登录用户尝试标记消息已读')
            return
            
        sender_id = data.get('sender_id')
        if not sender_id:
            logger.warning('未提供发送者ID')
            return
            
        try:
            # 标记消息为已读
            messages = Message.query.filter_by(
                sender_id=sender_id,
                recipient_id=session['user_id'],
                status='sent'
            ).all()
            
            for message in messages:
                message.status = 'read'
                message.read_at = datetime.utcnow()
            
            db.session.commit()
            logger.info('已将 %d 条消息标记为已读', len(messages))
            
        except Exception as e:
            logger.error('标记消息已读失败: %s', str(e), exc_info=True)
            db.session.rollback()

    @socketio.on('clear_history')
    def handle_clear_history():
        if 'user_id' not in session:
            logger.warning('未登录用户尝试清除历史记录')
            emit('error', {'message': '请先登录'})
            return
            
        try:
            # 清除聊天历史
            if ai_chat.clear_history(session['user_id']):
                logger.info('已清除用户 %s 的聊天历史', session['user_id'])
                emit('history_cleared')
            else:
                logger.warning('用户 %s 没有聊天历史可清除', session['user_id'])
                
        except Exception as e:
            logger.error('清除历史记录失败: %s', str(e), exc_info=True)
            emit('error', {'message': '清除历史记录失败'})
