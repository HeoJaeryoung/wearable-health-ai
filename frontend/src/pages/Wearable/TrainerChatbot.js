import React, { useState, useRef, useEffect } from 'react';
import { sendMessage } from '../../api/wearable';
import '../../css/wearable/TrainerChatbot.css';

const CHARACTERS = [
  { id: 'devil_coach', name: '악마 코치', icon: '😈' },
  { id: 'angel_coach', name: '천사 코치', icon: '😇' },
  { id: 'booster_coach', name: '부스터 코치', icon: '⚡' },
];

const QUICK_QUESTIONS = [
  '오늘 컨디션?',
  '피로 회복법',
  '식단 조언',
  '동기부여',
];

function TrainerChatbot() {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: '안녕! 나는 너의 트레이너야. 건강이나 운동에 대해 물어봐!',
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [character, setCharacter] = useState('devil_coach');
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async (messageText) => {
    const userMessage = messageText || input.trim();
    if (!userMessage || loading) return;

    setInput('');
    setMessages((prev) => [...prev, { role: 'user', content: userMessage }]);
    setLoading(true);

    try {
      const userId = localStorage.getItem('user_email') || 'guest@test.com';
      const response = await sendMessage(userId, userMessage, character);
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: response.reply || '응답을 받지 못했습니다.',
          character: response.character,
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: '죄송합니다. 오류가 발생했습니다. 다시 시도해주세요.',
          isError: true,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleQuickQuestion = (question) => {
    handleSend(question);
  };

  const currentCharacter = CHARACTERS.find((c) => c.id === character);

  return (
    <div className="chatbot-card">
      <div className="chatbot-header">
        <div className="chatbot-title">
          <span className="chatbot-icon">🤖</span>
          <h3>트레이너 챗봇</h3>
        </div>
        <div className="character-selector">
          {CHARACTERS.map((char) => (
            <button
              key={char.id}
              className={`character-btn ${
                character === char.id ? 'active' : ''
              }`}
              onClick={() => setCharacter(char.id)}
              title={char.name}
            >
              {char.icon}
            </button>
          ))}
        </div>
      </div>

      {/* 고정형 질의 버튼 */}
      <div className="quick-questions">
        {QUICK_QUESTIONS.map((question, index) => (
          <button
            key={index}
            className="quick-btn"
            onClick={() => handleQuickQuestion(question)}
            disabled={loading}
          >
            {question}
          </button>
        ))}
      </div>

      <div className="chatbot-messages">
        {messages.map((msg, index) => (
          <div
            key={index}
            className={`message ${msg.role} ${msg.isError ? 'error' : ''}`}
          >
            {msg.role === 'assistant' && (
              <span className="message-avatar">
                {currentCharacter?.icon || '🤖'}
              </span>
            )}
            <div className="message-content">{msg.content}</div>
          </div>
        ))}
        {loading && (
          <div className="message assistant">
            <span className="message-avatar">{currentCharacter?.icon}</span>
            <div className="message-content typing">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="chatbot-input">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="메시지를 입력하세요..."
          disabled={loading}
        />
        <button
          className="send-btn"
          onClick={() => handleSend()}
          disabled={!input.trim() || loading}
        >
          전송
        </button>
      </div>
    </div>
  );
}

export default TrainerChatbot;
