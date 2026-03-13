import React, { useState, useEffect } from 'react';
import { Search, SlidersHorizontal, Sparkles, ChevronRight } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import ProductCard from '../components/ProductCard';
import { MOCK_PRODUCTS } from '../constants';
import { Product, Category } from '../types';

const Home: React.FC = () => {
  const navigate = useNavigate();
  const [products, setProducts] = useState<Product[]>([]);
  const [activeCategory, setActiveCategory] = useState<string>('全部');
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    // Simulate loading data. In real app, fetch from API/Storage
    const stored = localStorage.getItem('products');
    if (stored) {
      setProducts([...MOCK_PRODUCTS, ...JSON.parse(stored)]);
    } else {
      setProducts(MOCK_PRODUCTS);
    }
  }, []);

  const categories = ['全部', ...Object.values(Category)];

  const filteredProducts = products.filter(p => {
    const matchesCategory = activeCategory === '全部' || p.category === activeCategory;
    const matchesSearch = p.title.toLowerCase().includes(searchTerm.toLowerCase()) || 
                          p.location.name.includes(searchTerm) ||
                          p.tags.some(t => t.includes(searchTerm));
    return matchesCategory && matchesSearch;
  });

  return (
    <div className="min-h-full bg-slate-50">
      {/* Header */}
      <header className="sticky top-0 bg-white/90 backdrop-blur-md z-40 px-4 py-3 border-b border-slate-200">
        <div className="flex items-center justify-between mb-3">
          <h1 className="text-xl font-bold bg-gradient-to-r from-orange-600 to-amber-600 bg-clip-text text-transparent">
            LocalTreasure
          </h1>
          <button className="p-2 text-slate-400 hover:text-slate-600">
            <SlidersHorizontal size={20} />
          </button>
        </div>
        
        {/* Search */}
        <div className="relative mb-3">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400" size={16} />
          <input 
            type="text"
            placeholder="搜索特产 / 地点 / 想要交换的物品..."
            className="w-full bg-slate-100 text-slate-800 text-sm rounded-full py-2.5 pl-10 pr-4 focus:outline-none focus:ring-2 focus:ring-orange-200"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        {/* Categories */}
        <div className="flex space-x-2 overflow-x-auto no-scrollbar pb-1">
          {categories.map(cat => (
            <button
              key={cat}
              onClick={() => setActiveCategory(cat)}
              className={`whitespace-nowrap px-4 py-1.5 rounded-full text-xs font-medium transition-colors ${
                activeCategory === cat 
                  ? 'bg-slate-900 text-white' 
                  : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
      </header>

      {/* New Today Banner */}
      <div className="px-4 pt-4">
        <button 
          onClick={() => navigate('/new-today')}
          className="w-full bg-gradient-to-r from-orange-50 to-amber-50 border border-orange-100 rounded-xl p-3 flex items-center justify-between hover:shadow-sm transition-all"
        >
          <div className="flex items-center gap-2">
            <div className="bg-orange-100 p-1.5 rounded-lg text-orange-500">
              <Sparkles size={18} />
            </div>
            <div className="text-left">
              <h3 className="text-sm font-bold text-orange-900">今日上新</h3>
              <p className="text-xs text-orange-600 mt-0.5">发现最新鲜的家乡味道</p>
            </div>
          </div>
          <ChevronRight size={20} className="text-orange-400" />
        </button>
      </div>

      {/* Product Grid */}
      <div className="p-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredProducts.map(product => (
          <ProductCard key={product.id} product={product} />
        ))}
        {filteredProducts.length === 0 && (
          <div className="col-span-full py-20 text-center">
            <p className="text-slate-400">没有找到相关特产，换个关键词试试？</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default Home;