import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Camera, Sparkles, X, Loader2, MapPin } from 'lucide-react';
import { generateProductDescription } from '../services/geminiService';
import { Category, Product } from '../types';
import { CURRENT_USER } from '../constants';

const Upload: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [aiLoading, setAiLoading] = useState(false);
  const [geoLoading, setGeoLoading] = useState(false);
  
  const [formData, setFormData] = useState({
    title: '',
    category: Category.FOOD,
    description: '',
    locationName: '',
    lat: 35.0, // Default fallback
    lng: 105.0, // Default fallback
    tags: '',
    exchangePreference: ''
  });
  
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        setPreviewUrl(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleAiGenerate = async () => {
    if (!formData.title) {
      alert("请先输入产品名称");
      return;
    }
    setAiLoading(true);
    const description = await generateProductDescription(
      formData.title,
      formData.category,
      formData.tags
    );
    setFormData(prev => ({ ...prev, description }));
    setAiLoading(false);
  };

  const handleGetCurrentLocation = () => {
    if (!navigator.geolocation) {
      alert("您的浏览器不支持地理位置功能");
      return;
    }
    setGeoLoading(true);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setFormData(prev => ({
          ...prev,
          lat: position.coords.latitude,
          lng: position.coords.longitude,
          locationName: prev.locationName || '当前位置 (已获取坐标)'
        }));
        setGeoLoading(false);
      },
      (error) => {
        console.error("Geolocation error:", error);
        alert("无法获取位置，请确保已授权。");
        setGeoLoading(false);
      }
    );
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    // Mock saving logic
    const newProduct: Product = {
      id: Date.now().toString(),
      title: formData.title,
      description: formData.description,
      imageUrl: previewUrl || 'https://picsum.photos/400/300?random=99',
      category: formData.category as Category,
      location: {
        lat: formData.lat, 
        lng: formData.lng, 
        name: formData.locationName || '未知地点'
      },
      ownerId: CURRENT_USER.id,
      ownerName: CURRENT_USER.name,
      tags: formData.tags.split(',').map(t => t.trim()),
      exchangePreference: formData.exchangePreference,
      reviews: [],
      rating: 0
    };

    // Save to local storage for demo persistence
    const existing = JSON.parse(localStorage.getItem('products') || '[]');
    localStorage.setItem('products', JSON.stringify([newProduct, ...existing]));

    setTimeout(() => {
      setLoading(false);
      navigate('/profile');
    }, 1000);
  };

  return (
    <div className="bg-white min-h-full pb-20">
      <div className="sticky top-0 bg-white z-10 px-4 py-4 flex items-center border-b border-slate-100">
        <button onClick={() => navigate(-1)} className="p-1 -ml-1 text-slate-500">
          <X size={24} />
        </button>
        <h1 className="flex-1 text-center font-bold text-lg">发布特产</h1>
        <div className="w-8"></div> {/* Spacer */}
      </div>

      <form onSubmit={handleSubmit} className="p-5 space-y-6">
        
        {/* Image Upload */}
        <div className="space-y-2">
          <label className="block text-sm font-medium text-slate-700">特产照片</label>
          <div className="relative aspect-video rounded-xl bg-slate-50 border-2 border-dashed border-slate-200 hover:border-orange-300 transition-colors flex flex-col items-center justify-center overflow-hidden">
             {previewUrl ? (
               <img src={previewUrl} alt="Preview" className="w-full h-full object-cover" />
             ) : (
               <div className="text-center p-4">
                 <Camera className="mx-auto h-10 w-10 text-slate-300" />
                 <p className="mt-2 text-xs text-slate-400">点击上传照片</p>
               </div>
             )}
             <input 
               type="file" 
               accept="image/*" 
               className="absolute inset-0 opacity-0 cursor-pointer"
               onChange={handleImageChange}
             />
          </div>
        </div>

        {/* Title */}
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">名称</label>
          <input
            required
            type="text"
            className="w-full px-4 py-3 rounded-lg bg-slate-50 border border-slate-200 focus:ring-2 focus:ring-orange-100 outline-none transition-all"
            placeholder="例如：正宗四川腊肠"
            value={formData.title}
            onChange={e => setFormData({...formData, title: e.target.value})}
          />
        </div>

        {/* Category & Location */}
        <div className="grid grid-cols-2 gap-4">
           <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">分类</label>
            <select
              className="w-full px-4 py-3 rounded-lg bg-slate-50 border border-slate-200 outline-none"
              value={formData.category}
              onChange={e => setFormData({...formData, category: e.target.value as Category})}
            >
              {Object.values(Category).map(c => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
           </div>
           <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">产地/交易点</label>
            <div className="relative">
              <input
                type="text"
                className="w-full pl-4 pr-10 py-3 rounded-lg bg-slate-50 border border-slate-200 outline-none"
                placeholder="例如：成都"
                value={formData.locationName}
                onChange={e => setFormData({...formData, locationName: e.target.value})}
              />
              <button 
                type="button"
                onClick={handleGetCurrentLocation}
                className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 text-slate-400 hover:text-orange-600 rounded-full hover:bg-orange-50 transition-colors"
                title="使用当前位置"
              >
                {geoLoading ? <Loader2 className="animate-spin" size={18} /> : <MapPin size={18} />}
              </button>
            </div>
           </div>
        </div>

        {/* Tags */}
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">关键词 (用逗号分隔)</label>
          <input
            type="text"
            className="w-full px-4 py-3 rounded-lg bg-slate-50 border border-slate-200 outline-none"
            placeholder="辣味, 手工, 传统"
            value={formData.tags}
            onChange={e => setFormData({...formData, tags: e.target.value})}
          />
        </div>

        {/* Description with AI Button */}
        <div>
          <div className="flex justify-between items-center mb-1">
            <label className="block text-sm font-medium text-slate-700">描述</label>
            <button
              type="button"
              onClick={handleAiGenerate}
              disabled={aiLoading}
              className="flex items-center text-xs font-bold text-orange-600 hover:text-orange-700 bg-orange-50 px-2 py-1 rounded-md transition-colors"
            >
              {aiLoading ? <Loader2 className="animate-spin mr-1" size={12}/> : <Sparkles size={12} className="mr-1" />}
              AI 帮我写
            </button>
          </div>
          <textarea
            required
            rows={4}
            className="w-full px-4 py-3 rounded-lg bg-slate-50 border border-slate-200 focus:ring-2 focus:ring-orange-100 outline-none transition-all"
            placeholder="介绍一下你的特产有什么特别之处..."
            value={formData.description}
            onChange={e => setFormData({...formData, description: e.target.value})}
          />
        </div>

        {/* Exchange Preference */}
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">想交换什么</label>
          <input
            type="text"
            className="w-full px-4 py-3 rounded-lg bg-slate-50 border border-slate-200 outline-none"
            placeholder="例如：海鲜，茶叶，或者任何惊喜"
            value={formData.exchangePreference}
            onChange={e => setFormData({...formData, exchangePreference: e.target.value})}
          />
        </div>

        {/* Submit */}
        <button
          type="submit"
          disabled={loading}
          className="w-full py-4 rounded-xl bg-slate-900 text-white font-bold text-lg shadow-lg hover:bg-slate-800 active:scale-95 transition-all flex items-center justify-center"
        >
          {loading ? <Loader2 className="animate-spin" /> : '发布特产'}
        </button>

      </form>
    </div>
  );
};

export default Upload;