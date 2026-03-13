export interface Review {
  id: string;
  userId: string;
  userName: string;
  userAvatar: string;
  rating: number;
  content: string;
  date: string;
}

export interface Product {
  id: string;
  title: string;
  description: string;
  imageUrl: string;
  category: string;
  location: {
    lat: number;
    lng: number;
    name: string; // City or Region name
  };
  ownerId: string;
  ownerName: string;
  tags: string[];
  exchangePreference: string; // What they want in return
  reviews: Review[];
  rating: number; // Average rating 0-5
}

export interface User {
  id: string;
  name: string;
  avatar: string;
  bio: string;
  joinedDate: string;
  stats: {
    exchanged: number;
    listed: number;
    rating: number;
  }
  exchangedProductIds?: string[];
}

export interface PostComment {
  id: string;
  userId: string;
  userName: string;
  userAvatar: string;
  content: string;
  time: string;
}

export interface Post {
  id: string;
  user: {
    id: string;
    name: string;
    avatar: string;
  };
  productId: string; // The product this post is about
  productName: string; // Snapshot of product name
  exchangedUsers: string[]; // List of user IDs who participated in this exchange
  time: string;
  content: string;
  images: string[];
  likes: number;
  comments: PostComment[];
  isLiked: boolean;
}

export enum Category {
  FOOD = '食品',
  CRAFT = '手工艺',
  DRINK = '酒水饮料',
  HERB = '药材',
  OTHER = '其他'
}