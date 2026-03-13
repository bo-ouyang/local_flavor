import React from 'react';
import { HashRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Home from './pages/Home';
import Upload from './pages/Upload';
import Profile from './pages/Profile';
import Community from './pages/Community';
import PostDetail from './pages/PostDetail';
import PublishPost from './pages/PublishPost';
import ProductDetail from './pages/ProductDetail';
import Chat from './pages/Chat';
import NewToday from './pages/NewToday';

const App: React.FC = () => {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/product/:id" element={<ProductDetail />} />
          <Route path="/upload" element={<Upload />} />
          <Route path="/profile" element={<Profile />} />
          <Route path="/community" element={<Community />} />
          <Route path="/community/post/:id" element={<PostDetail />} />
          <Route path="/community/publish" element={<PublishPost />} />
          <Route path="/chat/:userId" element={<Chat />} />
          <Route path="/new-today" element={<NewToday />} />
        </Routes>
      </Layout>
    </Router>
  );
};

export default App;