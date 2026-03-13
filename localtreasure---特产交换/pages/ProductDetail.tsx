import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, MapPin, Share2, Heart, Star, Send, User, AlertTriangle } from 'lucide-react';
import { Product, Review } from '../types';
import { MOCK_PRODUCTS, CURRENT_USER, CATEGORY_COLORS } from '../constants';

const ProductDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [product, setProduct] = useState<Product | null>(null);
  const [isFavorite, setIsFavorite] = useState(false);
  const [newReview, setNewReview] = useState('');
  const [rating, setRating] = useState(5);
  const [distance, setDistance] = useState<number | null>(null);

  // Load Product & Favorite status
  useEffect(() => {
    // 1. Get Product
    const storedProducts = JSON.parse(localStorage.getItem('products') || '[]');
    const allProducts = [...MOCK_PRODUCTS, ...storedProducts];
    const found = allProducts.find(p => p.id === id);
    if (found) {
        // Ensure reviews and rating exist if loading older data
        if (!found.reviews) found.reviews = [];
        if (typeof found.rating !== 'number') found.rating = 0;
        setProduct(found);
    }

    // 2. Check Favorite
    const favorites = JSON.parse(localStorage.getItem('userFavorites') || '[]');
    setIsFavorite(favorites.includes(id));
  }, [id]);

  // Calculate Distance when product is loaded
  useEffect(() => {
    if (product && navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          const userLat = position.coords.latitude;
          const userLng = position.coords.longitude;
          const prodLat = product.location.lat;
          const prodLng = product.location.lng;

          // Haversine formula
          const R = 6371; // Radius of the earth in km
          const dLat = (prodLat - userLat) * (Math.PI / 180);
          const dLon = (prodLng - userLng) * (Math.PI / 180);
          const a = 
            Math.sin(dLat/2) * Math.sin(dLat/2) +
            Math.cos(userLat * (Math.PI / 180)) * Math.cos(prodLat * (Math.PI / 180)) * 
            Math.sin(dLon/2) * Math.sin(dLon/2); 
          const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a)); 
          const d = R * c; // Distance in km
          
          setDistance(d);
        },
        (err) => {
          console.log("Error getting location:", err);
        }
      );
    }
  }, [product]);

  const toggleFavorite = () => {
    const favorites = JSON.parse(localStorage.getItem('userFavorites') || '[]');
    let newFavorites;
    if (isFavorite) {
      newFavorites = favorites.filter((fid: string) => fid !== id);
    } else {
      newFavorites = [...favorites, id];
    }
    localStorage.setItem('userFavorites', JSON.stringify(newFavorites));
    setIsFavorite(!isFavorite);
  };

  const submitReview = () => {
    if (!product || !newReview.trim()) return;

    const review: Review = {
      id: Date.now().toString(),
      userId: CURRENT_USER.id,
      userName: CURRENT_USER.name,
      userAvatar: CURRENT_USER.avatar,
      rating: rating,
      content: newReview,
      date: new Date().toISOString().split('T')[0]
    };

    const updatedReviews = [review, ...product.reviews];
    const avgRating = updatedReviews.reduce((acc, r) => acc + r.rating, 0) / updatedReviews.length;

    const updatedProduct = {
      ...product,
      reviews: updatedReviews,
      rating: avgRating
    };

    // Update State
    setProduct(updatedProduct);
    setNewReview('');

    // Update LocalStorage (This is a bit complex because we mix Mock and Local data)
    // For demo simplicity: We will update the 'products' key in localStorage.
    // If it was a mock product, we create a copy in localStorage to persist changes.
    const storedProducts = JSON.parse(localStorage.getItem('products') || '[]');
    const existingIndex = storedProducts.findIndex((p: Product) => p.id === product.id);
    
    let newStoredProducts;
    if (existingIndex >= 0) {
      storedProducts[existingIndex] = updatedProduct;
      newStoredProducts = storedProducts;
    } else {
      // It was from constants, so we add it to local storage to override/persist
      newStoredProducts = [...storedProducts, updatedProduct];
    }
    localStorage.setItem('products', JSON.stringify(newStoredProducts));
  };

  if (!product) return <div className="p-8 text-center text-slate-400">加载中...</div>;

  return (
    <div className="bg-slate-50 min-h-full pb-20">
      {/* Header Image */}
      <div className="relative h-64 md:h-80 w-full">
        <img src={product.imageUrl} alt={product.title} className="w-full h-full object-cover" />
        <div className="absolute top-0 left-0 right-0 p-4 flex justify-between items-start bg-gradient-to-b from-black/50 to-transparent">
          <button onClick={() => navigate(-1)} className="p-2 bg-white/20 backdrop-blur-md rounded-full text-white hover:bg-white/30 transition-all">
            <ArrowLeft size={24} />
          </button>
          <div className="flex space-x-2">
            <button className="p-2 bg-white/20 backdrop-blur-md rounded-full text-white hover:bg-white/30 transition-all">
              <Share2 size={24} />
            </button>
            <button 
              onClick={toggleFavorite}
              className={`p-2 backdrop-blur-md rounded-full transition-all ${isFavorite ? 'bg-red-500 text-white' : 'bg-white/20 text-white hover:bg-white/30'}`}
            >
              <Heart size={24} fill={isFavorite ? "currentColor" : "none"} />
            </button>
          </div>
        </div>
      </div>

      <div className="px-4 -mt-6 relative z-10">
        <div className="bg-white rounded-2xl p-5 shadow-sm border border-slate-100">
          
          {/* Distance Warning Alert */}
          {distance !== null && distance > 300 && (
            <div className="mb-4 bg-amber-50 border border-amber-200 rounded-xl p-3 flex items-start">
              <AlertTriangle className="text-amber-500 shrink-0 mr-2 mt-0.5" size={18} />
              <div>
                <p className="text-sm font-bold text-amber-800">距离提示</p>
                <p className="text-xs text-amber-700 mt-1 leading-relaxed">
                  该特产距离您约 <span className="font-bold">{Math.round(distance)}</span> 公里，距离较远，建议确认物流方式或选择邮寄交换。
                </p>
              </div>
            </div>
          )}

          <div className="flex justify-between items-start">
            <div>
               <span className={`inline-block px-2 py-1 rounded-md text-xs font-semibold mb-2 ${CATEGORY_COLORS[product.category]}`}>
                  {product.category}
               </span>
               <h1 className="text-xl font-bold text-slate-900 leading-tight">{product.title}</h1>
            </div>
            {product.rating > 0 && (
              <div className="flex flex-col items-end">
                 <div className="flex items-center bg-amber-50 px-2 py-1 rounded-lg text-amber-600 font-bold">
                    <Star size={16} className="fill-current mr-1"/>
                    {product.rating.toFixed(1)}
                 </div>
                 <span className="text-xs text-slate-400 mt-1">{product.reviews.length} 条评价</span>
              </div>
            )}
          </div>

          <div className="mt-4 flex items-center text-slate-500 text-sm">
             <MapPin size={16} className="mr-1 text-slate-400" />
             {product.location.name}
             {distance !== null && (
               <span className="ml-2 text-xs bg-slate-100 px-1.5 py-0.5 rounded text-slate-500">
                 距您 {Math.round(distance)} km
               </span>
             )}
          </div>

          <div className="mt-6 pt-6 border-t border-slate-100">
             <h3 className="font-bold text-slate-800 mb-2">想交换</h3>
             <div className="bg-orange-50 text-orange-800 p-3 rounded-lg text-sm">
                {product.exchangePreference}
             </div>
          </div>
          
          <div className="mt-6 pt-6 border-t border-slate-100">
             <h3 className="font-bold text-slate-800 mb-2">商品详情</h3>
             <p className="text-slate-600 leading-relaxed text-sm">
               {product.description}
             </p>
             <div className="mt-3 flex flex-wrap gap-2">
                {product.tags.map(tag => (
                   <span key={tag} className="text-xs text-slate-500 bg-slate-100 px-2 py-1 rounded-full">#{tag}</span>
                ))}
             </div>
          </div>
          
          {/* Owner Info */}
          <div className="mt-6 pt-6 border-t border-slate-100 flex items-center">
             <div className="w-10 h-10 rounded-full bg-slate-200 flex items-center justify-center overflow-hidden">
                <User size={20} className="text-slate-500"/>
             </div>
             <div className="ml-3 flex-1">
                <div className="text-sm font-bold text-slate-800">{product.ownerName}</div>
                <div className="text-xs text-slate-500">信誉良好 • 交易 12 次</div>
             </div>
             <div className="flex gap-2">
               <button 
                 onClick={() => {
                   alert('交换请求已发送！');
                 }}
                 className="px-4 py-2 bg-orange-500 hover:bg-orange-600 text-white text-sm font-bold rounded-lg transition-colors"
               >
                 交换
               </button>
               <button 
                 onClick={() => navigate(`/chat/${product.ownerId}`)} 
                 className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white text-sm font-bold rounded-lg transition-colors"
               >
                 联系TA
               </button>
             </div>
          </div>
        </div>

        {/* Reviews Section */}
        <div className="bg-white rounded-2xl p-5 shadow-sm border border-slate-100 mt-4">
           <h3 className="font-bold text-slate-800 mb-4 flex items-center">
             评价 <span className="text-slate-400 text-sm font-normal ml-2">({product.reviews.length})</span>
           </h3>

           {/* Add Review */}
           <div className="mb-6 bg-slate-50 p-3 rounded-xl">
              <div className="flex items-center mb-2">
                 {[1,2,3,4,5].map(star => (
                   <button key={star} onClick={() => setRating(star)} className="p-1">
                      <Star size={16} className={star <= rating ? "text-amber-400 fill-current" : "text-slate-300"} />
                   </button>
                 ))}
                 <span className="text-xs text-slate-400 ml-2">{rating} 分</span>
              </div>
              <div className="flex gap-2">
                 <input 
                    type="text" 
                    value={newReview}
                    onChange={e => setNewReview(e.target.value)}
                    placeholder="写下你的评价..."
                    className="flex-1 bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm outline-none focus:border-orange-300"
                 />
                 <button onClick={submitReview} disabled={!newReview.trim()} className="p-2 bg-orange-500 text-white rounded-lg disabled:opacity-50">
                    <Send size={18} />
                 </button>
              </div>
           </div>

           {/* Review List */}
           <div className="space-y-4">
              {product.reviews.map(review => (
                 <div key={review.id} className="border-b border-slate-50 last:border-0 pb-4 last:pb-0">
                    <div className="flex justify-between items-center mb-1">
                       <div className="flex items-center">
                          <img src={review.userAvatar} className="w-6 h-6 rounded-full mr-2 bg-slate-200" alt=""/>
                          <span className="text-sm font-medium text-slate-700">{review.userName}</span>
                       </div>
                       <span className="text-xs text-slate-400">{review.date}</span>
                    </div>
                    <div className="flex items-center mb-1">
                       {[...Array(5)].map((_, i) => (
                          <Star key={i} size={10} className={i < review.rating ? "text-amber-400 fill-current" : "text-slate-200"} />
                       ))}
                    </div>
                    <p className="text-slate-600 text-sm">{review.content}</p>
                 </div>
              ))}
              {product.reviews.length === 0 && (
                <div className="text-center py-4 text-slate-400 text-sm">暂无评价，快来抢沙发！</div>
              )}
           </div>
        </div>
      </div>
    </div>
  );
};

export default ProductDetail;