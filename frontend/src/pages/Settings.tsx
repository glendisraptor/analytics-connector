import { User, Database, Calendar, BarChart3, Bell, Shield, Cog } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { useAuth } from "@/contexts/AuthContext";

const Settings = () => {

    const {user, loading} = useAuth();

  const settingsTabs = [
    { value: "profile", label: "Profile", icon: User },
    { value: "connections", label: "Connections", icon: Database },
    { value: "scheduling", label: "Scheduling", icon: Calendar },
    { value: "analytics", label: "Analytics", icon: BarChart3 },
    { value: "notifications", label: "Notifications", icon: Bell },
    { value: "security", label: "Security", icon: Shield },
    { value: "system", label: "System", icon: Cog }
  ];

  return (
    <div className="p-6">
      <div className="max-w-7xl mx-auto space-y-8">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold text-foreground">Settings</h1>
          <p className="text-muted-foreground">Manage your account, connections, and system preferences</p>
        </div>

        {/* Settings Tabs */}
        <Tabs defaultValue="profile" className="space-y-6">
          <TabsList className="grid w-full grid-cols-4 lg:grid-cols-7 bg-muted/30">
            {settingsTabs.map((tab) => (
              <TabsTrigger 
                key={tab.value} 
                value={tab.value} 
                className="flex items-center gap-2 data-[state=active]:bg-gradient-primary data-[state=active]:text-primary-foreground"
              >
                <tab.icon className="w-4 h-4" />
                <span className="hidden sm:inline">{tab.label}</span>
              </TabsTrigger>
            ))}
          </TabsList>

          {/* Profile Tab */}
          <TabsContent value="profile">
            <Card className="bg-card/60 backdrop-blur-sm border-border/40 shadow-card">
              <CardHeader>
                <CardTitle className="text-foreground">Profile Information</CardTitle>
                <CardDescription>Update your personal information and account details</CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="flex items-center gap-6">
                  <Avatar className="w-20 h-20 border-4 border-primary/20">
                    <AvatarImage src="" />
                    <AvatarFallback className="bg-gradient-secondary text-secondary-foreground text-2xl font-semibold">
                      GM
                    </AvatarFallback>
                  </Avatar>
                  <div>
                    <h3 className="text-lg font-semibold text-foreground">Glen Mogane</h3>
                    <p className="text-muted-foreground">mogane@gmail.com</p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-2">
                    <Label htmlFor="fullName" className="text-foreground">Full Name</Label>
                    <Input 
                      id="fullName" 
                      value={loading ? 'Loading...' : user?.full_name || ''}
                      className="bg-muted/30 border-border/40"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="email" className="text-foreground">Email Address</Label>
                    <Input 
                      id="email" 
                    value={loading ? 'Loading...' : user?.email || ''}
                      className="bg-muted/30 border-border/40"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="username" className="text-foreground">Username</Label>
                    <Input 
                      id="username" 
                      disabled
                    value={loading ? 'Loading...' : user?.username || ''}
                      className="bg-muted/30 border-border/40"
                    />
                  </div>
                </div>

                <Button className="bg-gradient-primary text-primary-foreground hover:opacity-90 shadow-elevated">
                  Update Profile
                </Button>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Other tabs with placeholder content */}
          <TabsContent value="connections">
            <Card className="bg-card/60 backdrop-blur-sm border-border/40 shadow-card">
              <CardHeader>
                <CardTitle className="text-foreground">Connection Settings</CardTitle>
                <CardDescription>Configure default connection parameters and timeouts</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground">Connection settings configuration coming soon...</p>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="scheduling">
            <Card className="bg-card/60 backdrop-blur-sm border-border/40 shadow-card">
              <CardHeader>
                <CardTitle className="text-foreground">Scheduling Preferences</CardTitle>
                <CardDescription>Manage default sync schedules and timing preferences</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground">Scheduling preferences configuration coming soon...</p>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="analytics">
            <Card className="bg-card/60 backdrop-blur-sm border-border/40 shadow-card">
              <CardHeader>
                <CardTitle className="text-foreground">Analytics Settings</CardTitle>
                <CardDescription>Configure analytics platform integration and preferences</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground">Analytics settings configuration coming soon...</p>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="notifications">
            <Card className="bg-card/60 backdrop-blur-sm border-border/40 shadow-card">
              <CardHeader>
                <CardTitle className="text-foreground">Notification Preferences</CardTitle>
                <CardDescription>Choose how and when you want to be notified</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground">Notification preferences configuration coming soon...</p>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="security">
            <Card className="bg-card/60 backdrop-blur-sm border-border/40 shadow-card">
              <CardHeader>
                <CardTitle className="text-foreground">Security Settings</CardTitle>
                <CardDescription>Manage your account security and access controls</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground">Security settings configuration coming soon...</p>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="system">
            <Card className="bg-card/60 backdrop-blur-sm border-border/40 shadow-card">
              <CardHeader>
                <CardTitle className="text-foreground">System Preferences</CardTitle>
                <CardDescription>Configure system-wide settings and preferences</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground">System preferences configuration coming soon...</p>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

export default Settings;