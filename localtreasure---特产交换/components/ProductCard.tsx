import React from 'react';
import { MapPin, Repeat, Star } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Product } from '../types';
import { CATEGORY_COLORS } from '../constants';

interface ProductCardProps {
  product: Product;
}

const ProductCard: React.FC<ProductCardProps> = ({ product }) => {
  return (
    <Link to={`/product/${product.id}`} className="block group">
      <div className="bg-white rounded-xl overflow-hidden shadow-sm border border-slate-100 hover:shadow-md transition-shadow duration-300">
        <div className="relative h-48 w-full overflow-hidden">
          <img 
            src={product.imageUrl} 
            alt={product.title} 
            className="w-full h-full object-cover transform group-hover:scale-105 transition-transform duration-500"
          />
          <div className="absolute top-2 left-2">
            <span className={`px-2 py-1 rounded-md text-xs font-semibold ${CATEGORY_COLORS[product.category] || 'bg-gray-100 text-gray-800'}`}>
              {product.category}
            </span>
          </div>
        </div>
        
        <div className="p-4">
          <div className="flex justify-between items-start mb-2">
            <h3 className="font-bold text-lg text-slate-800 line-clamp-1 flex-1 mr-2">{product.title}</h3>
            {product.rating > 0 && (
              <div className="flex items-center text-amber-500 text-xs font-bold whitespace-nowrap bg-amber-50 px-1.5 py-0.5 rounded">
                <Star size={10} className="fill-current mr-0.5" />
                {product.rating.toFixed(1)}
              </div>
            )}
          </div>
          
          <div className="flex items-center text-slate-500 text-xs mb-3">
            <MapPin size={12} className="mr-1" />
            <span className="truncate max-w-[80px]">{product.location.name}</span>
            <span className="mx-2">•</span>
            <span className="truncate">{product.ownerName}</span>
          </div>

          <p className="text-slate-600 text-sm line-clamp-2 mb-4 h-10">
            {product.description}
          </p>

          <div className="bg-orange-50 p-2 rounded-lg border border-orange-100">
            <div className="flex items-start text-orange-700 text-xs font-medium">
              <Repeat size={14} className="mr-1 mt-0.5 shrink-0" />
              <span className="line-clamp-1">想换: {product.exchangePreference}</span>
            </div>
          </div>
        </div>
      </div>
    </Link>
  );
};

export default ProductCard;