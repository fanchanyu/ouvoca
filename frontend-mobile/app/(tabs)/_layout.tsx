// 底部 Tab 導航
import { Tabs } from 'expo-router'
import { Text } from 'react-native'

export default function TabLayout() {
  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: '#2563eb',
        tabBarInactiveTintColor: '#94a3b8',
        headerStyle: { backgroundColor: '#2563eb' },
        headerTintColor: '#fff',
        tabBarStyle: {
          backgroundColor: '#fff',
          borderTopWidth: 1,
          borderTopColor: '#e2e8f0',
          paddingTop: 6,
          paddingBottom: 6,
          height: 60,
        },
      }}
    >
      <Tabs.Screen
        name="dashboard"
        options={{
          title: '儀表板',
          tabBarLabel: '儀表板',
          tabBarIcon: ({ focused }) => <Text style={{ fontSize: 22 }}>{focused ? '📊' : '📊'}</Text>,
        }}
      />
      <Tabs.Screen
        name="inventory"
        options={{
          title: '庫存',
          tabBarLabel: '庫存',
          tabBarIcon: ({ focused }) => <Text style={{ fontSize: 22 }}>📦</Text>,
        }}
      />
      <Tabs.Screen
        name="scan"
        options={{
          title: '掃 QR',
          tabBarLabel: '掃 QR',
          tabBarIcon: ({ focused }) => <Text style={{ fontSize: 22 }}>📷</Text>,
        }}
      />
      <Tabs.Screen
        name="chat"
        options={{
          title: 'AI 助手',
          tabBarLabel: 'AI 助手',
          tabBarIcon: ({ focused }) => <Text style={{ fontSize: 22 }}>💬</Text>,
        }}
      />
      <Tabs.Screen
        name="me"
        options={{
          title: '我的',
          tabBarLabel: '我的',
          tabBarIcon: ({ focused }) => <Text style={{ fontSize: 22 }}>👤</Text>,
        }}
      />
    </Tabs>
  )
}
