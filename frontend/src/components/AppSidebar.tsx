import { NavLink, useLocation } from "react-router-dom";
import {
  Home,
  Database,
  BarChart3,
  GitBranch,
  Settings,
  LogOut,
  FileText,
} from "lucide-react";
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarTrigger,
  useSidebar,
} from "@/components/ui/sidebar";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";

const menuItems = [
  { title: "Dashboard", url: "/", icon: Home },
  { title: "Connections", url: "/connections", icon: Database },
  { title: "Analytics", url: "/analytics", icon: BarChart3 },
  { title: "ETL Dashboard", url: "/etl", icon: GitBranch },
  { title: "Data Extraction", url: "/data-extraction", icon: FileText },
  { title: "Settings", url: "/settings", icon: Settings },
];

export function AppSidebar() {
  const { state } = useSidebar();
  const location = useLocation();
  const currentPath = location.pathname;

  const isActive = (path: string) => currentPath === path;
  const isCollapsed = state === "collapsed";

  const getNavClass = ({ isActive }: { isActive: boolean }) =>
    isActive 
      ? "bg-sidebar-primary text-sidebar-primary-foreground font-semibold shadow-sm" 
      : "hover:bg-sidebar-accent text-sidebar-foreground hover:text-sidebar-primary transition-all duration-200";

  return (
    <TooltipProvider>
      <Sidebar className="border-r border-sidebar-border bg-sidebar backdrop-blur-sm">
        <SidebarContent className="p-0 flex flex-col h-full">
          {/* Logo/Header with colored background */}
          <div className="bg-gradient-primary rounded-br-2xl p-6 mb-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-white/20 rounded-xl flex items-center justify-center backdrop-blur-sm">
                <BarChart3 className="w-5 h-5 text-white" />
              </div>
              {!isCollapsed && (
                <div>
                  <h2 className="font-bold text-lg text-white">
                    Analytics Connector
                  </h2>
                  <p className="text-xs text-white/80">Data Management</p>
                </div>
              )}
            </div>
          </div>

          {/* Navigation - flex-1 to push user section to bottom */}
          <div className={isCollapsed ? "px-2 flex-1" : "px-3 flex-1"}>
            <SidebarGroup>
              {!isCollapsed && (
                <SidebarGroupLabel className="text-xs text-sidebar-foreground/60 uppercase tracking-wide px-2 mb-2">
                  Navigation
                </SidebarGroupLabel>
              )}
              <SidebarGroupContent>
                <SidebarMenu className="space-y-1">
                  {menuItems.map((item) => (
                    <SidebarMenuItem key={item.title}>
                      {isCollapsed ? (
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <NavLink 
                              to={item.url} 
                              end 
                              className={({ isActive }) => `
                                flex items-center justify-center w-10 h-10 rounded-lg transition-all duration-200 mx-auto
                                ${getNavClass({ isActive })}
                              `}
                            >
                              <item.icon className="w-5 h-5" />
                            </NavLink>
                          </TooltipTrigger>
                          <TooltipContent side="right" className="font-medium">
                            {item.title}
                          </TooltipContent>
                        </Tooltip>
                      ) : (
                        <SidebarMenuButton asChild>
                          <NavLink 
                            to={item.url} 
                            end 
                            className={({ isActive }) => `
                              flex items-center gap-3 px-3 py-2 rounded-lg transition-all duration-200
                              ${getNavClass({ isActive })}
                            `}
                          >
                            <item.icon className="w-5 h-5" />
                            <span className="font-medium">{item.title}</span>
                          </NavLink>
                        </SidebarMenuButton>
                      )}
                    </SidebarMenuItem>
                  ))}
                </SidebarMenu>
              </SidebarGroupContent>
            </SidebarGroup>
          </div>

          {/* User Profile - positioned at bottom */}
          <div className={isCollapsed ? "px-2 pb-4 border-t border-sidebar-border" : "px-3 pb-4 border-t border-sidebar-border"}>
            <div className={isCollapsed ? "flex flex-col items-center py-4 space-y-2" : "flex items-center gap-3 px-2 py-4"}>
              {isCollapsed ? (
                <>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Avatar className="w-8 h-8 border-2 border-sidebar-primary/20 cursor-pointer">
                        <AvatarImage src="" />
                        <AvatarFallback className="bg-gradient-secondary text-sidebar-primary-foreground text-xs font-semibold">
                          GM
                        </AvatarFallback>
                      </Avatar>
                    </TooltipTrigger>
                    <TooltipContent side="right" className="font-medium">
                      <p>Glen Mogane</p>
                      <p className="text-xs opacity-70">mogane@gmail.com</p>
                    </TooltipContent>
                  </Tooltip>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <button className="flex items-center justify-center w-8 h-8 rounded-lg text-sidebar-foreground/60 hover:text-sidebar-foreground hover:bg-sidebar-accent transition-colors">
                        <LogOut className="w-4 h-4" />
                      </button>
                    </TooltipTrigger>
                    <TooltipContent side="right" className="font-medium">
                      Logout
                    </TooltipContent>
                  </Tooltip>
                </>
              ) : (
                <>
                  <Avatar className="w-8 h-8 border-2 border-sidebar-primary/20">
                    <AvatarImage src="" />
                    <AvatarFallback className="bg-gradient-secondary text-sidebar-primary-foreground text-xs font-semibold">
                      GM
                    </AvatarFallback>
                  </Avatar>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-sidebar-foreground">Glen Mogane</p>
                    <p className="text-xs text-sidebar-foreground/60">mogane@gmail.com</p>
                  </div>
                </>
              )}
            </div>
            {!isCollapsed && (
              <button className="w-full flex items-center gap-3 px-2 py-2 text-sm text-sidebar-foreground/60 hover:text-sidebar-foreground transition-colors rounded-lg hover:bg-sidebar-accent">
                <LogOut className="w-4 h-4" />
                Logout
              </button>
            )}
          </div>
        </SidebarContent>
      </Sidebar>
    </TooltipProvider>
  );
}