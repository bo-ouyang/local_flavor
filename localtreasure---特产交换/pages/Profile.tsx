import React, { useEffect, useState } from 'react';
import { Settings, MapPin, Calendar, Star, Package, Heart } from 'lucide-react';
import { CURRENT_USER, MOCK_PRODUCTS } from '../constants';
import { Product } from '../types';
import ProductCard from '../components/ProductCard';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell } from 'recharts';

const Profile: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'listings' | 'favorites'>('listings');
  const [myProducts, setMyProducts] = useState<Product[]>([]);
  const [myFavorites, setMyFavorites] = useState<Product[]>([]);

  useEffect(() => {
    const storedProducts = JSON.parse(localStorage.getItem('products') || '[]');
    const allProducts = [...MOCK_PRODUCTS, ...storedProducts];
    
    // 1. My Listings
    const userProducts = allProducts.filter(p => p.ownerId === CURRENT_USER.id);
    setMyProducts(userProducts);

    // 2. My Favorites
    const favoriteIds = JSON.parse(localStorage.getItem('userFavorites') || '[]');
    const userFavorites = allProducts.filter(p => favoriteIds.includes(p.id));
    setMyFavorites(userFavorites);
  }, []);

  const statsData = [
    { name: '交换', value: CURRENT_USER.stats.exchanged },
    { name: '在架', value: myProducts.length || CURRENT_USER.stats.listed },
    { name: '评分', value: CURRENT_USER.stats.rating },
  ];

  return (
    <div className="bg-slate-50 min-h-full">
      {/* Profile Header */}
      <div className="bg-white pb-6 rounded-b-[2rem] shadow-sm overflow-hidden">
        <div className="h-32 bg-gradient-to-r from-orange-400 to-amber-300 relative">
            <button className="absolute top-4 right-4 p-2 bg-white/20 backdrop-blur-md rounded-full text-white hover:bg-white/30 transition-all">
                <Settings size={20} />
            </button>
        </div>
        <div className="px-6 -mt-12 flex flex-col items-center">
          <div className="relative">
            <img 
              src={CURRENT_USER.avatar} 
              alt={CURRENT_USER.name} 
              className="w-24 h-24 rounded-full border-4 border-white shadow-md object-cover"
            />
            <div className="absolute bottom-0 right-0 bg-green-500 w-5 h-5 rounded-full border-2 border-white"></div>
          </div>
          
          <h2 className="mt-3 text-xl font-bold text-slate-800">{CURRENT_USER.name}</h2>
          <div className="flex items-center text-slate-500 text-xs mt-1 space-x-3">
             <span className="flex items-center"><MapPin size={12} className="mr-1"/> 成都</span>
             <span className="flex items-center"><Calendar size={12} className="mr-1"/> 加入于 {CURRENT_USER.joinedDate}</span>
          </div>
          
          <p className="mt-4 text-center text-slate-600 text-sm max-w-xs">
            {CURRENT_USER.bio}
          </p>

          {/* Stats Cards */}
          <div className="grid grid-cols-3 gap-4 w-full mt-6">
             <div className="bg-slate-50 p-3 rounded-2xl text-center border border-slate-100">
                <div className="text-xl font-bold text-slate-800">{CURRENT_USER.stats.exchanged}</div>
                <div className="text-xs text-slate-400 mt-1">成功交换</div>
             </div>
             <div className="bg-slate-50 p-3 rounded-2xl text-center border border-slate-100">
                <div className="text-xl font-bold text-slate-800">{myProducts.length}</div>
                <div className="text-xs text-slate-400 mt-1">在架商品</div>
             </div>
             <div className="bg-slate-50 p-3 rounded-2xl text-center border border-slate-100">
                <div className="flex items-center justify-center text-xl font-bold text-slate-800">
                    {CURRENT_USER.stats.rating} <Star size={14} className="text-yellow-400 fill-current ml-1"/>
                </div>
                <div className="text-xs text-slate-400 mt-1">信誉评分</div>
             </div>
          </div>
        </div>
      </div>

      {/* Activity Chart */}
      <div className="px-4 mt-6">
        <h3 className="font-bold text-slate-800 mb-4 px-2">活跃数据</h3>
        <div className="h-48 bg-white rounded-xl p-4 shadow-sm border border-slate-100">
            <ResponsiveContainer width="100%" height="100%">
                <BarChart data={statsData} layout="vertical" margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                    <XAxis type="number" hide />
                    <YAxis dataKey="name" type="category" tick={{fontSize: 12}} width={40} axisLine={false} tickLine={false} />
                    <Tooltip cursor={{fill: 'transparent'}} />
                    <Bar dataKey="value" barSize={20} radius={[0, 10, 10, 0]}>
                      {statsData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={index === 0 ? '#f97316' : index === 1 ? '#3b82f6' : '#fbbf24'} />
                      ))}
                    </Bar>
                </BarChart>
            </ResponsiveContainer>
        </div>
      </div>

      {/* Tabs */}
      <div className="px-4 mt-6">
          <div className="flex bg-slate-100 rounded-xl p-1 mb-4">
              <button 
                  onClick={() => setActiveTab('listings')}
                  className={`flex-1 py-2 text-sm font-bold rounded-lg transition-all ${activeTab === 'listings' ? 'bg-white shadow-sm text-slate-800' : 'text-slate-500'}`}
              >
                  我的发布
              </button>
              <button 
                  onClick={() => setActiveTab('favorites')}
                  className={`flex-1 py-2 text-sm font-bold rounded-lg transition-all flex items-center justify-center ${activeTab === 'favorites' ? 'bg-white shadow-sm text-red-500' : 'text-slate-500'}`}
              >
                  <Heart size={14} className={`mr-1 ${activeTab === 'favorites' ? 'fill-current' : ''}`} />
                  我的收藏
              </button>
          </div>

         {/* Content */}
         <div className="pb-24">
             {activeTab === 'listings' ? (
                 myProducts.length > 0 ? (
                     <div className="space-y-4">
                         {myProducts.map(p => (
                             <ProductCard key={p.id} product={p} />
                         ))}
                     </div>
                 ) : (
                     <div className="flex flex-col items-center justify-center py-12 bg-white rounded-xl border border-dashed border-slate-200">
                         <Package size={48} className="text-slate-300 mb-3" />
                         <p className="text-slate-400 text-sm">还没有发布任何特产</p>
                     </div>
                 )
             ) : (
                 myFavorites.length > 0 ? (
                    <div className="space-y-4">
                        {myFavorites.map(p => (
                            <ProductCard key={p.id} product={p} />
                        ))}
                    </div>
                 ) : (
                    <div className="flex flex-col items-center justify-center py-12 bg-white rounded-xl border border-dashed border-slate-200">
                        <Heart size={48} className="text-slate-300 mb-3" />
                        <p className="text-slate-400 text-sm">还没有收藏任何商品</p>
                    </div>
                 )
             )}
         </div>
      </div>
    </div>
  );
};

export default Profile;