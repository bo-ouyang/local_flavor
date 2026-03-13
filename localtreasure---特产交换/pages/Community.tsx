import React, { useState, useEffect } from 'react';
import { Heart, MessageCircle, Share2, Sparkles, Plus } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { MOCK_POSTS } from '../constants';
import { Post } from '../types';

const Community: React.FC = () => {
  const navigate = useNavigate();
  const [posts, setPosts] = useState<Post[]>([]);

  useEffect(() => {
    const storedPosts = JSON.parse(localStorage.getItem('community_posts') || '[]');
    setPosts([...storedPosts, ...MOCK_POSTS]);
  }, []);

  const toggleLike = (e: React.MouseEvent, id: string) => {
    e.stopPropagation(); // Prevent navigating to detail page
    const updatedPosts = posts.map(post => {
      if (post.id === id) {
        return {
          ...post,
          isLiked: !post.isLiked,
          likes: post.isLiked ? post.likes - 1 : post.likes + 1
        };
      }
      return post;
    });
    setPosts(updatedPosts);
    
    // Update local storage for persisted likes
    const storedPosts = JSON.parse(localStorage.getItem('community_posts') || '[]');
    const postToUpdate = updatedPosts.find(p => p.id === id);
    if (postToUpdate) {
      const existingIndex = storedPosts.findIndex((p: Post) => p.id === id);
      if (existingIndex >= 0) {
        storedPosts[existingIndex] = postToUpdate;
        localStorage.setItem('community_posts', JSON.stringify(storedPosts));
      } else {
        localStorage.setItem('community_posts', JSON.stringify([postToUpdate, ...storedPosts]));
      }
    }
  };

  return (
    <div className="min-h-full bg-slate-50 pb-20 relative">
      {/* Header */}
      <header className="sticky top-0 bg-white/90 backdrop-blur-md z-40 px-4 py-3 border-b border-slate-200 flex items-center justify-between">
        <h1 className="text-lg font-bold text-slate-900 flex items-center gap-2">
          <Sparkles className="text-orange-500" size={20} />
          特产交流社区
        </h1>
      </header>

      {/* Feed */}
      <div className="p-4 space-y-4">
        {posts.map(post => (
          <div 
            key={post.id} 
            onClick={() => navigate(`/community/post/${post.id}`)}
            className="bg-white rounded-2xl p-4 shadow-sm border border-slate-100 cursor-pointer hover:shadow-md transition-shadow"
          >
            {/* User Info */}
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-3">
                <img src={post.user.avatar} alt={post.user.name} className="w-10 h-10 rounded-full bg-slate-200 object-cover" referrerPolicy="no-referrer" />
                <div>
                  <h3 className="text-sm font-bold text-slate-800">{post.user.name}</h3>
                  <p className="text-xs text-slate-400">{post.time}</p>
                </div>
              </div>
              <button 
                onClick={(e) => e.stopPropagation()}
                className="text-xs font-medium text-orange-500 bg-orange-50 px-3 py-1 rounded-full"
              >
                关注
              </button>
            </div>

            {/* Content */}
            <div className="mb-3">
              <span className="inline-block bg-orange-100 text-orange-800 text-[10px] px-2 py-0.5 rounded mb-1">
                相关特产: {post.productName}
              </span>
              <p className="text-sm text-slate-700 leading-relaxed line-clamp-3">
                {post.content}
              </p>
            </div>

            {/* Images */}
            <div className={`grid gap-2 mb-4 ${post.images.length > 1 ? 'grid-cols-2' : 'grid-cols-1'}`}>
              {post.images.map((img, idx) => (
                <img key={idx} src={img} alt="分享图片" className="w-full h-40 object-cover rounded-xl border border-slate-100" referrerPolicy="no-referrer" />
              ))}
            </div>

            {/* Actions */}
            <div className="flex items-center justify-between pt-3 border-t border-slate-50 text-slate-500">
              <button onClick={(e) => e.stopPropagation()} className="flex items-center gap-1.5 hover:text-slate-700 transition-colors">
                <Share2 size={18} />
                <span className="text-xs">分享</span>
              </button>
              <button className="flex items-center gap-1.5 hover:text-slate-700 transition-colors">
                <MessageCircle size={18} />
                <span className="text-xs">{post.comments.length}</span>
              </button>
              <button 
                onClick={(e) => toggleLike(e, post.id)}
                className={`flex items-center gap-1.5 transition-colors ${post.isLiked ? 'text-red-500' : 'hover:text-slate-700'}`}
              >
                <Heart size={18} fill={post.isLiked ? "currentColor" : "none"} />
                <span className="text-xs">{post.likes}</span>
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Floating Publish Button */}
      <button 
        onClick={() => navigate('/community/publish')}
        className="fixed bottom-24 right-4 w-14 h-14 bg-orange-500 text-white rounded-full shadow-lg flex items-center justify-center hover:bg-orange-600 hover:scale-105 transition-all z-50"
      >
        <Plus size={28} />
      </button>
    </div>
  );
};

export default Community;
