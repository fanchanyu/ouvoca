// 進入點：根據是否已登入決定去登入頁或主介面
import { Redirect } from 'expo-router'
import { useAuthStore } from '../src/store/auth'

export default function Index() {
  const token = useAuthStore((s) => s.token)
  return <Redirect href={token ? '/(tabs)/dashboard' : '/login'} />
}
