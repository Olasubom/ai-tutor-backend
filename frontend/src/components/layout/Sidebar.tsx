import { NavLink } from 'react-router-dom';
import { GraduationCap } from 'lucide-react';
import { cn } from '@/lib/utils';
export interface NavItem {
  to: string;
  label: string;
  icon: React.ReactNode;
  onClick?: () => void;
}

interface SidebarProps {
  items: NavItem[];
  bottomItems?: NavItem[];
  subtitle?: string;
}

export function Sidebar({ items, bottomItems, subtitle = 'LEARNING INTELLIGENCE' }: SidebarProps) {
  return (
    <aside className="fixed left-0 top-0 z-40 flex h-screen w-[260px] flex-col border-r border-border bg-sidebar">
      <div className="flex items-center gap-3 border-b border-border px-6 py-5">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary text-white">
          <GraduationCap className="h-5 w-5" />
        </div>
        <div>
          <div className="text-[16px] font-bold text-text-primary">AITutor</div>
          <div className="label-caps text-text-muted">{subtitle}</div>
        </div>
      </div>

      <nav className="flex-1 space-y-1 px-3 py-4">
        {items.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 rounded-lg px-4 py-2.5 text-[14px] transition-colors',
                isActive
                  ? 'border-l-[3px] border-primary bg-card-hover font-medium text-primary'
                  : 'border-l-[3px] border-transparent text-text-secondary hover:text-text-primary',
              )
            }
          >
            {item.icon}
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div className="mt-auto border-t border-border p-4">
        {bottomItems?.map((item) =>
          item.onClick ? (
            <button
              key={item.label}
              type="button"
              onClick={item.onClick}
              className="mb-1 flex w-full items-center gap-3 rounded-lg px-4 py-2 text-left text-[14px] text-text-secondary hover:bg-card-hover"
            >
              {item.icon}
              {item.label}
            </button>
          ) : (
            <NavLink
              key={item.to}
              to={item.to}
              className="mb-1 flex items-center gap-3 rounded-lg px-4 py-2 text-[14px] text-text-secondary hover:bg-card-hover"
            >
              {item.icon}
              {item.label}
            </NavLink>
          ),
        )}
      </div>
    </aside>
  );
}
