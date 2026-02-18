"use client";

import { useTheme } from "next-themes";
import {
  BarChart3,
  TrendingUp,
  Settings,
  FlaskConical,
  TestTube2,
  Play,
  Sun,
  Moon,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { TABS, type TabKey } from "@/lib/constants";

const ICON_MAP = {
  BarChart3,
  TrendingUp,
  Settings,
  FlaskConical,
  TestTube2,
  Play,
} as const;

interface DashboardHeaderProps {
  activeTab: TabKey;
  onTabChange: (tab: TabKey) => void;
}

export function DashboardHeader({
  activeTab,
  onTabChange,
}: DashboardHeaderProps) {
  const { theme, setTheme } = useTheme();

  return (
    <header className="sticky top-0 z-50 border-b border-border/50 bg-background/80 backdrop-blur-md">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3">
        {/* Logo */}
        <h1 className="text-lg font-bold tracking-tight">D2trader</h1>

        {/* Tabs */}
        <nav className="hidden md:flex items-center gap-1">
          {TABS.map((tab) => {
            const Icon = ICON_MAP[tab.icon as keyof typeof ICON_MAP];
            const isActive = activeTab === tab.key;
            return (
              <button
                key={tab.key}
                onClick={() => onTabChange(tab.key)}
                className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                }`}
              >
                <Icon className="h-4 w-4" />
                {tab.label}
              </button>
            );
          })}
        </nav>

        {/* Actions */}
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          >
            <Sun className="h-4 w-4 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
            <Moon className="absolute h-4 w-4 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
            <span className="sr-only">테마 전환</span>
          </Button>
        </div>
      </div>

      {/* Mobile tabs */}
      <div className="flex md:hidden overflow-x-auto border-t border-border/50 px-2">
        {TABS.map((tab) => {
          const Icon = ICON_MAP[tab.icon as keyof typeof ICON_MAP];
          const isActive = activeTab === tab.key;
          return (
            <button
              key={tab.key}
              onClick={() => onTabChange(tab.key)}
              className={`flex shrink-0 items-center gap-1 px-3 py-2 text-xs font-medium transition-colors ${
                isActive
                  ? "border-b-2 border-primary text-primary"
                  : "text-muted-foreground"
              }`}
            >
              <Icon className="h-3.5 w-3.5" />
              {tab.label}
            </button>
          );
        })}
      </div>
    </header>
  );
}
