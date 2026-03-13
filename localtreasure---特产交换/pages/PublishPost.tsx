import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, ImagePlus, Send } from 'lucide-react';
import { CURRENT_USER, MOCK_PRODUCTS } from '../constants';
import { Product, Post } from '../types';

const PublishPost: React.FC = () => {
  const navigate = useNavigate();
  const [content, setContent] = useState('');
  const [selectedProductId, setSelectedProductId] = useState<string>('');
  const [exchangedProducts, setExchangedProducts] = useState<Product[]>([]);

  useEffect(() => {
    // Load all products to find the ones the user has exchanged
    const storedProducts = JSON.parse(localStorage.getItem('products') || '[]');
    const allProducts = [...MOCK_PRODUCTS, ...storedProducts];
    
    // Filter products that the user has exchanged
    const userExchangedIds = CURRENT_USER.exchangedProductIds || [];
    const userExchangedProducts = allProducts.filter(p => userExchangedIds.includes(p.id));
    
    setExchangedProducts(userExchangedProducts);
    if (userExchangedProducts.length > 0) {
      setSelectedProductId(userExchangedProducts[0].id);
    }
  }, []);

  const handlePublish = () => {
    if (!content.trim() || !selectedProductId) return;

    const selectedProduct = exchangedProducts.find(p => p.id === selectedProductId);
    if (!selectedProduct) return;

    const newPost: Post = {
      id: `post_${Date.now()}`,
      user: {
        id: CURRENT_USER.id,
        name: CURRENT_USER.name,
        avatar: CURRENT_USER.avatar
      },
      productId: selectedProduct.id,
      productName: selectedProduct.title,
      exchangedUsers: [CURRENT_USER.id, selectedProduct.ownerId], // Assuming current user and owner exchanged
      time: '刚刚',
      content: content,
      images: ['https://picsum.photos/seed/newpost/400/300'], // Mock image for demo
      likes: 0,
      comments: [],
      isLiked: false
    };

    const storedPosts = JSON.parse(localStorage.getItem('community_posts') || '[]');
    localStorage.setItem('community_posts', JSON.stringify([newPost, ...storedPosts]));

    navigate('/community');
  };

  return (
    <div className="min-h-full bg-slate-50 pb-20">
      {/* Header */}
      <header className="sticky top-0 bg-white/90 backdrop-blur-md z-40 px-4 py-3 border-b border-slate-200 flex items-center justify-between">
        <div className="flex items-center">
          <button onClick={() => navigate(-1)} className="p-2 -ml-2 text-slate-600 hover:bg-slate-100 rounded-full transition-colors">
            <ArrowLeft size={24} />
          </button>
          <h1 className="ml-2 text-lg font-bold text-slate-900">发布动态</h1>
        </div>
        <button 
          onClick={handlePublish}
          disabled={!content.trim() || !selectedProductId}
          className="flex items-center gap-1 bg-orange-500 text-white px-4 py-1.5 rounded-full text-sm font-medium disabled:opacity-50"
        >
          <Send size={16} />
          发布
        </button>
      </header>

      <div className="p-4">
        {/* Product Selection */}
        <div className="mb-6">
          <label className="block text-sm font-bold text-slate-700 mb-2">关联交换过的特产</label>
          {exchangedProducts.length > 0 ? (
            <select 
              value={selectedProductId}
              onChange={(e) => setSelectedProductId(e.target.value)}
              className="w-full bg-white border border-slate-200 rounded-xl px-4 py-3 text-sm text-slate-700 outline-none focus:border-orange-500"
            >
              {exchangedProducts.map(p => (
                <option key={p.id} value={p.id}>{p.title}</option>
              ))}
            </select>
          ) : (
            <div className="bg-orange-50 text-orange-600 p-3 rounded-xl text-sm">
              您还没有交换过任何特产，无法发布动态。
            </div>
          )}
          <p className="text-xs text-slate-400 mt-2">只能发布自己交换过的商品的交流帖子</p>
        </div>

        {/* Content Input */}
        <div className="mb-4">
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="分享你的交换体验、收到的特产味道如何..."
            className="w-full h-40 bg-white border border-slate-200 rounded-xl p-4 text-sm text-slate-700 outline-none focus:border-orange-500 resize-none"
            disabled={exchangedProducts.length === 0}
          />
        </div>

        {/* Image Upload Mock */}
        <div>
          <button 
            disabled={exchangedProducts.length === 0}
            className="w-24 h-24 bg-white border-2 border-dashed border-slate-200 rounded-xl flex flex-col items-center justify-center text-slate-400 hover:border-orange-300 hover:text-orange-500 transition-colors disabled:opacity-50 disabled:hover:border-slate-200 disabled:hover:text-slate-400"
          >
            <ImagePlus size={24} className="mb-1" />
            <span className="text-xs">添加图片</span>
          </button>
        </div>
      </div>
    </div>
  );
};

export default PublishPost;
