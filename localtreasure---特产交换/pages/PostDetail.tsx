import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Heart, MessageCircle, Share2, Send, AlertCircle } from 'lucide-react';
import { CURRENT_USER, MOCK_POSTS } from '../constants';
import { Post, PostComment } from '../types';

const PostDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [post, setPost] = useState<Post | null>(null);
  const [newComment, setNewComment] = useState('');

  useEffect(() => {
    // Load posts from local storage or mock
    const storedPosts = JSON.parse(localStorage.getItem('community_posts') || '[]');
    const allPosts = [...storedPosts, ...MOCK_POSTS];
    const found = allPosts.find((p: Post) => p.id === id);
    if (found) {
      setPost(found);
    }
  }, [id]);

  const toggleLike = () => {
    if (!post) return;
    const updatedPost = {
      ...post,
      isLiked: !post.isLiked,
      likes: post.isLiked ? post.likes - 1 : post.likes + 1
    };
    setPost(updatedPost);

    // Update in local storage
    const storedPosts = JSON.parse(localStorage.getItem('community_posts') || '[]');
    const existingIndex = storedPosts.findIndex((p: Post) => p.id === post.id);
    if (existingIndex >= 0) {
      storedPosts[existingIndex] = updatedPost;
      localStorage.setItem('community_posts', JSON.stringify(storedPosts));
    } else {
      // It was a mock post, we can save it to local storage to persist the like
      localStorage.setItem('community_posts', JSON.stringify([updatedPost, ...storedPosts]));
    }
  };

  const submitComment = () => {
    if (!post || !newComment.trim()) return;

    const comment: PostComment = {
      id: Date.now().toString(),
      userId: CURRENT_USER.id,
      userName: CURRENT_USER.name,
      userAvatar: CURRENT_USER.avatar,
      content: newComment,
      time: '刚刚'
    };

    const updatedPost = {
      ...post,
      comments: [...post.comments, comment]
    };
    setPost(updatedPost);
    setNewComment('');

    // Update in local storage
    const storedPosts = JSON.parse(localStorage.getItem('community_posts') || '[]');
    const existingIndex = storedPosts.findIndex((p: Post) => p.id === post.id);
    if (existingIndex >= 0) {
      storedPosts[existingIndex] = updatedPost;
      localStorage.setItem('community_posts', JSON.stringify(storedPosts));
    } else {
      localStorage.setItem('community_posts', JSON.stringify([updatedPost, ...storedPosts]));
    }
  };

  if (!post) return <div className="p-8 text-center text-slate-400">加载中...</div>;

  const canComment = post.exchangedUsers.includes(CURRENT_USER.id);

  return (
    <div className="min-h-full bg-slate-50 pb-20">
      {/* Header */}
      <header className="sticky top-0 bg-white/90 backdrop-blur-md z-40 px-4 py-3 border-b border-slate-200 flex items-center">
        <button onClick={() => navigate(-1)} className="p-2 -ml-2 text-slate-600 hover:bg-slate-100 rounded-full transition-colors">
          <ArrowLeft size={24} />
        </button>
        <h1 className="ml-2 text-lg font-bold text-slate-900">动态详情</h1>
      </header>

      {/* Post Content */}
      <div className="bg-white p-4 mb-2">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <img src={post.user.avatar} alt={post.user.name} className="w-10 h-10 rounded-full bg-slate-200 object-cover" referrerPolicy="no-referrer" />
            <div>
              <h3 className="text-sm font-bold text-slate-800">{post.user.name}</h3>
              <p className="text-xs text-slate-400">{post.time}</p>
            </div>
          </div>
          <button className="text-xs font-medium text-orange-500 bg-orange-50 px-3 py-1 rounded-full">关注</button>
        </div>

        <div className="mb-3">
          <span className="inline-block bg-orange-100 text-orange-800 text-xs px-2 py-1 rounded mb-2">
            相关特产: {post.productName}
          </span>
          <p className="text-sm text-slate-700 leading-relaxed whitespace-pre-wrap">
            {post.content}
          </p>
        </div>

        <div className={`grid gap-2 mb-4 ${post.images.length > 1 ? 'grid-cols-2' : 'grid-cols-1'}`}>
          {post.images.map((img, idx) => (
            <img key={idx} src={img} alt="分享图片" className="w-full h-48 object-cover rounded-xl border border-slate-100" referrerPolicy="no-referrer" />
          ))}
        </div>

        <div className="flex items-center justify-between pt-3 border-t border-slate-50 text-slate-500">
          <button className="flex items-center gap-1.5 hover:text-slate-700 transition-colors">
            <Share2 size={18} />
            <span className="text-xs">分享</span>
          </button>
          <div className="flex items-center gap-4">
            <button className="flex items-center gap-1.5 hover:text-slate-700 transition-colors">
              <MessageCircle size={18} />
              <span className="text-xs">{post.comments.length}</span>
            </button>
            <button 
              onClick={toggleLike}
              className={`flex items-center gap-1.5 transition-colors ${post.isLiked ? 'text-red-500' : 'hover:text-slate-700'}`}
            >
              <Heart size={18} fill={post.isLiked ? "currentColor" : "none"} />
              <span className="text-xs">{post.likes}</span>
            </button>
          </div>
        </div>
      </div>

      {/* Comments Section */}
      <div className="bg-white p-4 min-h-[300px]">
        <h3 className="font-bold text-slate-800 mb-4 flex items-center">
          评论 <span className="text-slate-400 text-sm font-normal ml-2">({post.comments.length})</span>
        </h3>

        {/* Comment Input */}
        <div className="mb-6">
          {canComment ? (
            <div className="flex gap-2">
              <input 
                type="text" 
                value={newComment}
                onChange={e => setNewComment(e.target.value)}
                placeholder="写下你的评论..."
                className="flex-1 bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none focus:border-orange-300"
              />
              <button 
                onClick={submitComment} 
                disabled={!newComment.trim()} 
                className="p-2 bg-orange-500 text-white rounded-lg disabled:opacity-50"
              >
                <Send size={18} />
              </button>
            </div>
          ) : (
            <div className="bg-slate-50 rounded-lg p-3 flex items-center justify-center text-slate-500 text-sm">
              <AlertCircle size={16} className="mr-2" />
              只有参与过该商品交换的用户才能评论
            </div>
          )}
        </div>

        {/* Comment List */}
        <div className="space-y-4">
          {post.comments.map(comment => (
            <div key={comment.id} className="flex gap-3">
              <img src={comment.userAvatar} className="w-8 h-8 rounded-full bg-slate-200 object-cover" alt="" referrerPolicy="no-referrer" />
              <div className="flex-1 border-b border-slate-50 pb-3">
                <div className="flex justify-between items-center mb-1">
                  <span className="text-sm font-medium text-slate-700">{comment.userName}</span>
                  <span className="text-xs text-slate-400">{comment.time}</span>
                </div>
                <p className="text-slate-600 text-sm">{comment.content}</p>
              </div>
            </div>
          ))}
          {post.comments.length === 0 && (
            <div className="text-center py-8 text-slate-400 text-sm">暂无评论</div>
          )}
        </div>
      </div>
    </div>
  );
};

export default PostDetail;
