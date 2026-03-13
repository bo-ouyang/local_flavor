import React from 'react';
import { Home, PlusCircle, MessageSquare, User } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const location = useLocation();

  const isActive = (path: string) => location.pathname === path;

  const NavItem = ({ to, icon: Icon, label }: { to: string; icon: any; label: string }) => (
    <Link
      to={to}
      className={`flex flex-col items-center justify-center w-full h-full transition-colors duration-200 ${
        isActive(to) 
          ? 'text-orange-600' 
          : 'text-slate-400 hover:text-slate-600'
      }`}
    >
      <Icon size={24} strokeWidth={isActive(to) ? 2.5 : 2} />
      <span className="text-[10px] mt-1 font-medium">{label}</span>
    </Link>
  );

  return (
    <div className="flex flex-col h-screen bg-slate-50 overflow-hidden font-sans">
      {/* Main Content Area */}
      <main className="flex-1 overflow-y-auto pb-20 no-scrollbar">
        {children}
      </main>

      {/* Bottom Navigation Bar - Fixed */}
      <nav className="fixed bottom-0 left-0 right-0 h-16 bg-white border-t border-slate-200 flex items-center justify-around z-50 pb-safe shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.05)]">
        <NavItem to="/" icon={Home} label="首页" />
        <NavItem to="/community" icon={MessageSquare} label="社区" />
        {/* Upload Button - Prominent */}
        <div className="relative -top-5">
           <Link to="/upload" className="flex items-center justify-center w-14 h-14 rounded-full bg-gradient-to-tr from-orange-500 to-amber-500 text-white shadow-lg hover:shadow-xl hover:scale-105 transition-all">
             <PlusCircle size={32} />
           </Link>
        </div>
        <NavItem to="/profile" icon={User} label="我的" />
      </nav>
    </div>
  );
};

export default Layout;