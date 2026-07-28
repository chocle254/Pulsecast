'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { ShieldAlert, Map, Database, History, Info, Activity } from 'lucide-react';

export default function Navbar() {
  const pathname = usePathname();

  const navItems = [
    { href: '/', label: 'Priority Queue', icon: ShieldAlert },
    { href: '/map', label: 'Regional Map', icon: Map },
    { href: '/evidence', label: 'Evidence Trail', icon: Database },
    { href: '/backtest', label: 'Backtest', icon: History },
    { href: '/about', label: 'Methodology', icon: Info },
  ];

  return (
    <header className="header-nav">
      <div className="container nav-inner">
        <Link href="/" className="brand-logo">
          <div className="brand-icon">
            <Activity className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="brand-title">PULSECAST</span>
              <span className="brand-subtitle">NDMA early-alert</span>
            </div>
          </div>
        </Link>

        <nav>
          <ul className="nav-links">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href || (item.href !== '/' && pathname.startsWith(item.href));
              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    className={`nav-link ${isActive ? 'active' : ''}`}
                  >
                    <Icon className="w-4 h-4" />
                    <span>{item.label}</span>
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>
      </div>
    </header>
  );
}
