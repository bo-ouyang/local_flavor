import { Product, User, Category } from './types';

export const CURRENT_USER: User = {
  id: 'u1',
  name: '旅行者阿杰',
  avatar: 'https://picsum.photos/200/200?random=user1',
  bio: '热爱寻找各地隐藏的美味，专注于云贵川特产交换。',
  joinedDate: '2023-10-15',
  stats: {
    exchanged: 12,
    listed: 5,
    rating: 4.8
  },
  exchangedProductIds: ['p2', 'p4', 'p5'] // Mocking that the current user has exchanged these products
};

export const MOCK_PRODUCTS: Product[] = [
  {
    id: 'p1',
    title: '自制四川麻辣香肠',
    description: '外婆秘制配方，选用土猪肉，烟熏30天。口感麻辣鲜香，非常适合下酒或炒饭。',
    imageUrl: 'https://picsum.photos/400/300?random=1',
    category: Category.FOOD,
    location: { lat: 30.6, lng: 104.0, name: '四川·成都' },
    ownerId: 'u1',
    ownerName: '旅行者阿杰',
    tags: ['腊味', '川味', '手工'],
    exchangePreference: '想换云南菌子或沿海干货',
    reviews: [
      {
        id: 'r1',
        userId: 'u2',
        userName: '江南茶客',
        userAvatar: 'https://picsum.photos/200/200?random=user2',
        rating: 5,
        content: '味道非常正宗，麻辣适中，包装也很仔细！',
        date: '2023-11-01'
      }
    ],
    rating: 5.0
  },
  {
    id: 'p2',
    title: '杭州西湖龙井明前茶',
    description: '正宗狮峰山产区，今年清明前采摘。色泽嫩绿，香气馥郁。',
    imageUrl: 'https://picsum.photos/400/300?random=2',
    category: Category.DRINK,
    location: { lat: 30.2, lng: 120.1, name: '浙江·杭州' },
    ownerId: 'u2',
    ownerName: '江南茶客',
    tags: ['绿茶', '春茶'],
    exchangePreference: '换西北牛羊肉干',
    reviews: [],
    rating: 0
  },
  {
    id: 'p3',
    title: '苏绣团扇 - 兰花',
    description: '苏州绣娘纯手工制作，双面绣工艺，图案栩栩如生。',
    imageUrl: 'https://picsum.photos/400/300?random=3',
    category: Category.CRAFT,
    location: { lat: 31.3, lng: 120.6, name: '江苏·苏州' },
    ownerId: 'u3',
    ownerName: '绣坊小雅',
    tags: ['非遗', '手工艺'],
    exchangePreference: '换具有民族特色的银饰',
    reviews: [],
    rating: 0
  },
  {
    id: 'p4',
    title: '云南野生牛肝菌干片',
    description: '香格里拉深山采摘，自然晾晒，无硫磺熏制。炖鸡汤一绝。',
    imageUrl: 'https://picsum.photos/400/300?random=4',
    category: Category.FOOD,
    location: { lat: 25.0, lng: 102.7, name: '云南·昆明' },
    ownerId: 'u4',
    ownerName: '山里人',
    tags: ['菌菇', '养生'],
    exchangePreference: '换海鲜干货',
    reviews: [],
    rating: 0
  },
  {
    id: 'p5',
    title: '新疆阿克苏冰糖心苹果',
    description: '核心产区，糖度极高，每一个都有冰糖心。',
    imageUrl: 'https://picsum.photos/400/300?random=5',
    category: Category.FOOD,
    location: { lat: 41.1, lng: 80.2, name: '新疆·阿克苏' },
    ownerId: 'u5',
    ownerName: '西域果农',
    tags: ['水果', '特产'],
    exchangePreference: '换南方热带水果',
    reviews: [],
    rating: 0
  }
];

export const CATEGORY_COLORS: Record<string, string> = {
  [Category.FOOD]: 'bg-orange-100 text-orange-800 border-orange-200',
  [Category.CRAFT]: 'bg-purple-100 text-purple-800 border-purple-200',
  [Category.DRINK]: 'bg-green-100 text-green-800 border-green-200',
  [Category.HERB]: 'bg-emerald-100 text-emerald-800 border-emerald-200',
  [Category.OTHER]: 'bg-gray-100 text-gray-800 border-gray-200',
};

import { Post } from './types';

export const MOCK_POSTS: Post[] = [
  {
    id: 'post1',
    user: { id: 'u2', name: '李阿姨', avatar: 'https://picsum.photos/seed/user1/100/100' },
    productId: 'p2',
    productName: '杭州西湖龙井明前茶',
    exchangedUsers: ['u1', 'u2'], // u1 (current user) participated
    time: '2小时前',
    content: '今天收到了来自新疆的特产大礼包！葡萄干超级甜，还有核桃和红枣，太感谢@张大哥 了！下次我给你寄我们这儿的腊肉。',
    images: ['https://picsum.photos/seed/xinjiang1/400/300', 'https://picsum.photos/seed/xinjiang2/400/300'],
    likes: 24,
    comments: [
      { id: 'c1', userId: 'u1', userName: '旅行者阿杰', userAvatar: 'https://picsum.photos/200/200?random=user1', content: '哈哈，好吃就行！', time: '1小时前' }
    ],
    isLiked: false
  },
  {
    id: 'post2',
    user: { id: 'u3', name: '吃货小王', avatar: 'https://picsum.photos/seed/user2/100/100' },
    productId: 'p3',
    productName: '苏绣团扇 - 兰花',
    exchangedUsers: ['u3', 'u4'], // u1 did NOT participate
    time: '5小时前',
    content: '第一次尝试正宗的柳州螺蛳粉，这味道简直绝了！虽然闻着臭，但吃起来是真的香。感谢广西的朋友分享~',
    images: ['https://picsum.photos/seed/luosifen/400/300'],
    likes: 112,
    comments: [],
    isLiked: true
  },
  {
    id: 'post3',
    user: { id: 'u4', name: '江南烟雨', avatar: 'https://picsum.photos/seed/user3/100/100' },
    productId: 'p4',
    productName: '云南野生牛肝菌干片',
    exchangedUsers: ['u1', 'u4'], // u1 participated
    time: '昨天',
    content: '用自家做的龙井茶换到了东北的榛子和松子，满满一大箱，东北的朋友太实在了！晚上边看电视边剥松子，美滋滋。',
    images: ['https://picsum.photos/seed/songzi/400/300'],
    likes: 89,
    comments: [],
    isLiked: false
  }
];