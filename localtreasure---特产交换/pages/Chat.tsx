import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Send, User } from 'lucide-react';

const Chat: React.FC = () => {
  const { userId } = useParams<{ userId: string }>();
  const navigate = useNavigate();
  const [message, setMessage] = useState('');
  const [messages, setMessages] = useState([
    { id: 1, text: '你好！我对你的特产很感兴趣。', sender: 'me', time: '10:00' },
    { id: 2, text: '你好！你想用什么来交换呢？', sender: 'them', time: '10:05' }
  ]);

  const handleSend = () => {
    if (!message.trim()) return;
    const newMessage = {
      id: Date.now(),
      text: message,
      sender: 'me',
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };
    setMessages([...messages, newMessage]);
    setMessage('');
  };

  return (
    <div className="flex flex-col h-full bg-slate-50">
      {/* Header */}
      <div className="bg-white border-b border-slate-200 px-4 py-3 flex items-center sticky top-0 z-10">
        <button onClick={() => navigate(-1)} className="p-2 -ml-2 text-slate-600 hover:bg-slate-100 rounded-full transition-colors">
          <ArrowLeft size={24} />
        </button>
        <div className="ml-2 flex items-center">
          <div className="w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center overflow-hidden">
            <User size={16} className="text-slate-500" />
          </div>
          <span className="ml-2 font-bold text-slate-800">用户 {userId}</span>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg) => (
          <div key={msg.id} className={`flex ${msg.sender === 'me' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[75%] rounded-2xl px-4 py-2 ${msg.sender === 'me' ? 'bg-orange-500 text-white rounded-tr-sm' : 'bg-white border border-slate-200 text-slate-800 rounded-tl-sm'}`}>
              <p className="text-sm">{msg.text}</p>
              <p className={`text-[10px] mt-1 text-right ${msg.sender === 'me' ? 'text-orange-200' : 'text-slate-400'}`}>{msg.time}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Input */}
      <div className="bg-white border-t border-slate-200 p-3 pb-safe">
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSend()}
            placeholder="输入消息..."
            className="flex-1 bg-slate-100 border-transparent focus:bg-white focus:border-orange-500 border rounded-full px-4 py-2 text-sm outline-none transition-all"
          />
          <button
            onClick={handleSend}
            disabled={!message.trim()}
            className="p-2 bg-orange-500 text-white rounded-full disabled:opacity-50 hover:bg-orange-600 transition-colors"
          >
            <Send size={20} />
          </button>
        </div>
      </div>
    </div>
  );
};

export default Chat;
