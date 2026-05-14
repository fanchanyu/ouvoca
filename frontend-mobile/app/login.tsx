/**
 * Login 頁 — 美術精緻化 + Demo Mode
 */
import { useState, useEffect } from 'react'
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet,
  Alert, ActivityIndicator, KeyboardAvoidingView, Platform,
} from 'react-native'
import { LinearGradient } from 'expo-linear-gradient'
import { router } from 'expo-router'
import { apiLogin, apiHealth, ApiError } from '../src/lib/api'
import { useAuthStore } from '../src/store/auth'

export default function LoginScreen() {
  const setAuth = useAuthStore((s) => s.setAuth)
  const loginAsDemo = useAuthStore((s) => s.loginAsDemo)
  const [username, setUsername] = useState('admin')
  const [password, setPassword] = useState('admin123')
  const [loading, setLoading] = useState(false)
  const [demoBypass, setDemoBypass] = useState(false)
  const [version, setVersion] = useState('')

  useEffect(() => {
    apiHealth()
      .then((h) => {
        setDemoBypass(h.demo_bypass)
        setVersion(h.version)
      })
      .catch(() => {})
  }, [])

  async function handleLogin() {
    setLoading(true)
    try {
      const res = await apiLogin(username, password)
      setAuth(res.access_token, {
        id: res.user.id,
        username: res.user.username,
        employee_id: res.user.employee_id,
        is_superuser: res.user.is_superuser,
      })
      router.replace('/(tabs)/dashboard')
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : '無法連線到後端 / Cannot reach backend'
      Alert.alert('登入失敗 Login failed', msg)
    } finally {
      setLoading(false)
    }
  }

  function handleDemo() {
    loginAsDemo()
    router.replace('/(tabs)/dashboard')
  }

  return (
    <LinearGradient colors={['#1e3a8a', '#2563eb', '#3b82f6']} style={styles.container}>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={styles.card}
      >
        <View style={styles.logoBox}>
          <Text style={styles.logoText}>L</Text>
        </View>
        <Text style={styles.title}>LLM-ERP</Text>
        <Text style={styles.subtitle}>
          AI-Native ERP {version ? `· v${version}` : ''}
        </Text>

        <View style={styles.field}>
          <Text style={styles.label}>帳號 / Username</Text>
          <TextInput
            style={styles.input}
            value={username}
            onChangeText={setUsername}
            autoCapitalize="none"
            autoCorrect={false}
          />
        </View>

        <View style={styles.field}>
          <Text style={styles.label}>密碼 / Password</Text>
          <TextInput
            style={styles.input}
            value={password}
            onChangeText={setPassword}
            secureTextEntry
          />
        </View>

        <TouchableOpacity
          style={[styles.btn, styles.btnPrimary]}
          onPress={handleLogin}
          disabled={loading}
        >
          {loading ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.btnTextPrimary}>登入 / Sign In</Text>
          )}
        </TouchableOpacity>

        {demoBypass && (
          <>
            <View style={styles.divider}>
              <View style={styles.line} />
              <Text style={styles.dividerText}>或 / or</Text>
              <View style={styles.line} />
            </View>

            <TouchableOpacity style={[styles.btn, styles.btnDemo]} onPress={handleDemo}>
              <Text style={styles.btnTextDemo}>✨ Demo 模式 / Demo Mode</Text>
            </TouchableOpacity>
          </>
        )}
      </KeyboardAvoidingView>
    </LinearGradient>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: 'center', padding: 20 },
  card: {
    backgroundColor: '#fff',
    borderRadius: 24,
    padding: 30,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.2,
    shadowRadius: 20,
    elevation: 10,
  },
  logoBox: {
    width: 60, height: 60, borderRadius: 16,
    backgroundColor: '#2563eb',
    alignSelf: 'center',
    justifyContent: 'center', alignItems: 'center',
    marginBottom: 16,
  },
  logoText: { color: '#fff', fontSize: 32, fontWeight: '700' },
  title: { fontSize: 28, fontWeight: '700', textAlign: 'center', color: '#0f172a' },
  subtitle: { fontSize: 13, color: '#64748b', textAlign: 'center', marginTop: 4, marginBottom: 24 },
  field: { marginBottom: 16 },
  label: { fontSize: 13, fontWeight: '500', color: '#475569', marginBottom: 6 },
  input: {
    borderWidth: 1, borderColor: '#cbd5e1',
    borderRadius: 10, paddingHorizontal: 14, paddingVertical: 12,
    fontSize: 15, backgroundColor: '#f8fafc',
  },
  btn: { borderRadius: 10, paddingVertical: 14, alignItems: 'center' },
  btnPrimary: { backgroundColor: '#2563eb', marginTop: 8 },
  btnTextPrimary: { color: '#fff', fontSize: 16, fontWeight: '600' },
  btnDemo: { backgroundColor: '#fef3c7', borderWidth: 1, borderColor: '#fde68a' },
  btnTextDemo: { color: '#92400e', fontSize: 14, fontWeight: '600' },
  divider: { flexDirection: 'row', alignItems: 'center', marginVertical: 16 },
  line: { flex: 1, height: 1, backgroundColor: '#e2e8f0' },
  dividerText: { paddingHorizontal: 10, fontSize: 12, color: '#94a3b8' },
})
