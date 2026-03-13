import React, { useState, useEffect } from 'react';
import { ArrowLeft, Sparkles } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import ProductCard from '../components/ProductCard';
import { MOCK_PRODUCTS } from '../constants';
import { Product } from '../types';

const NewToday: React.FC = () => {
  const navigate = useNavigate();
  const [products, setProducts] = useState<Product[]>([]);

  useEffect(() => {
    // Simulate loading new data. In real app, fetch from API with a date filter
    const stored = localStorage.getItem('products');
    let allProducts = MOCK_PRODUCTS;
    if (stored) {
      allProducts = [...MOCK_PRODUCTS, ...JSON.parse(stored)];
    }
    
    // Just mock "new today" by taking the first few or shuffling
    // For demo, we'll just reverse the list to show "newest" first
    setProducts(allProducts.reverse().slice(0, 6));
  }, []);

  return (
    <div className="min-h-full bg-slate-50 pb-20">
      {/* Header */}
      <header className="sticky top-0 bg-white/90 backdrop-blur-md z-40 px-4 py-3 border-b border-slate-200 flex items-center">
        <button onClick={() => navigate(-1)} className="p-2 -ml-2 text-slate-600 hover:bg-slate-100 rounded-full transition-colors">
          <ArrowLeft size={24} />
        </button>
        <h1 className="ml-2 text-lg font-bold text-slate-900 flex items-center gap-2">
          <Sparkles className="text-orange-500" size={20} />
          今日上新
        </h1>
      </header>

      {/* Product Grid */}
      <div className="p-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {products.map(product => (
          <ProductCard key={product.id} product={product} />
        ))}
        {products.length === 0 && (
          <div className="col-span-full py-20 text-center">
            <p className="text-slate-400">今日暂无上新，去看看其他特产吧</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default NewToday;
