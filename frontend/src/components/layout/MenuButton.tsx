import { Menu } from 'lucide-react';
import { useUiStore } from '@/stores/uiStore';

export function MenuButton() {
  const openSidebar = useUiStore((s) => s.openSidebar);

  return (
    <button
      type="button"
      aria-label="Open menu"
      onClick={openSidebar}
      className="rounded-lg p-2 hover:bg-card-hover lg:hidden"
    >
      <Menu className="h-5 w-5 text-text-secondary" />
    </button>
  );
}
