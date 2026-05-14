/**
 * 我的 / Me — 個人資料 + 設定 + 登出
 */
import { useEffect, useState } from 'react'
import {
  View, Text, TouchableOpacity, StyleSheet, ScrollView, Alert,
} from 'react-native'
import { router } from 'expo-router'
import { useAuthStore } from '../../src/store/auth'
import { apiHealth, API_BASE, HealthResponse } from '../../src/lib/api'

export default function Me() {
  const user = useAuthStore((s) => s.user)
  const logout = useAuthStore((s) => s.logout)
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const isDemo = user?.username === 'demo'

  useEffect(() => {
    apiHealth().then(setHealth).catch(() => {})
  }, [])

  function handleLogout() {
    Alert.alert(
      '確認登出 / Confirm logout',
      '確定要登出嗎？/ Are you sure?',
      [
        { text: '取消 / Cancel', style: 'cancel' },
        {
          text: '登出 / Logout',
          style: 'destructive',
          onPress: () => {
            logout()
            router.replace('/login')
          },
        },
      ],
    )
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* 頭像 + 名稱 */}
      <View style={styles.profileCard}>
        <View style={styles.avatar}>
          <Text style={styles.avatarText}>
            {user?.username?.[0]?.toUpperCase() || 'U'}
          </Text>
        </View>
        <Text style={styles.name}>{user?.username || '未登入'}</Text>
        <Text style={styles.subtitle}>
          {user?.is_superuser ? '👑 系統管理員 / Admin' : '👤 員工 / Staff'}
        </Text>
        {isDemo && (
          <View style={styles.demoBadge}>
            <Text style={styles.demoBadgeText}>✨ DEMO MODE</Text>
          </View>
        )}
      </View>

      {/* 用戶資訊 */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>帳號資訊 / Account Info</Text>
        <InfoRow label="使用者名稱 / Username" value={user?.username || '-'} />
        <InfoRow label="員工編號 / Employee ID" value={user?.employee_id || '-'} />
        <InfoRow
          label="權限 / Permission"
          value={user?.is_superuser ? '完整權限 / Full Access' : '一般員工 / Staff'}
        />
      </View>

      {/* 系統資訊 */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>系統資訊 / System Info</Text>
        <InfoRow label="後端位址 / API" value={API_BASE} />
        <InfoRow label="版本 / Version" value={health?.version || '...'} />
        <InfoRow label="LLM 提供者 / LLM" value={health?.llm_provider || '...'} />
        <InfoRow label="資料庫 / DB" value={health?.db || '...'} />
      </View>

      {/* 動作 */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>動作 / Actions</Text>
        <TouchableOpacity
          style={styles.actionRow}
          onPress={() =>
            Alert.alert(
              '關於 / About',
              'LLM-ERP Mobile\n版本 v2.0.0\nAI-Native ERP for SMB Manufacturers\n\n© 2026 LLM-ERP Project',
            )
          }
        >
          <Text style={styles.actionIcon}>ℹ️</Text>
          <Text style={styles.actionText}>關於 / About</Text>
          <Text style={styles.actionArrow}>›</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.actionRow}
          onPress={() =>
            Alert.alert(
              '說明 / Help',
              '前往 GitHub 取得最新文件：\nhttps://github.com/your-org/llm-erp',
            )
          }
        >
          <Text style={styles.actionIcon}>📚</Text>
          <Text style={styles.actionText}>使用說明 / User Guide</Text>
          <Text style={styles.actionArrow}>›</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.actionRow}
          onPress={() =>
            Alert.alert(
              '聯絡支援 / Contact Support',
              '電子郵件 Email：support@llm-erp.example\nLINE：@llmerp',
            )
          }
        >
          <Text style={styles.actionIcon}>📞</Text>
          <Text style={styles.actionText}>聯絡支援 / Contact</Text>
          <Text style={styles.actionArrow}>›</Text>
        </TouchableOpacity>
      </View>

      {/* 登出 */}
      <TouchableOpacity style={styles.logoutBtn} onPress={handleLogout}>
        <Text style={styles.logoutText}>🚪 登出 / Logout</Text>
      </TouchableOpacity>

      <Text style={styles.footer}>
        LLM-ERP Mobile · v{health?.version || '2.0.0'}
        {'\n'}AI-Native ERP for SMB Manufacturers
      </Text>
    </ScrollView>
  )
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.infoRow}>
      <Text style={styles.infoLabel}>{label}</Text>
      <Text style={styles.infoValue} numberOfLines={1}>
        {value}
      </Text>
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f8fafc' },
  content: { padding: 16, paddingBottom: 40 },

  profileCard: {
    backgroundColor: '#fff',
    borderRadius: 16,
    padding: 24,
    alignItems: 'center',
    marginBottom: 16,
    shadowColor: '#000',
    shadowOpacity: 0.05,
    shadowOffset: { width: 0, height: 2 },
    shadowRadius: 8,
    elevation: 2,
  },
  avatar: {
    width: 80, height: 80, borderRadius: 40,
    backgroundColor: '#2563eb',
    justifyContent: 'center', alignItems: 'center',
    marginBottom: 12,
  },
  avatarText: { color: '#fff', fontSize: 32, fontWeight: '700' },
  name: { fontSize: 22, fontWeight: '700', color: '#0f172a', marginBottom: 4 },
  subtitle: { fontSize: 13, color: '#64748b' },
  demoBadge: {
    backgroundColor: '#fef3c7',
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 12,
    marginTop: 8,
  },
  demoBadgeText: { fontSize: 11, color: '#92400e', fontWeight: '600' },

  section: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
  },
  sectionTitle: {
    fontSize: 13,
    fontWeight: '600',
    color: '#475569',
    marginBottom: 12,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },

  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#f1f5f9',
  },
  infoLabel: { fontSize: 13, color: '#64748b', flex: 1 },
  infoValue: {
    fontSize: 13,
    color: '#0f172a',
    fontWeight: '500',
    maxWidth: '60%',
    textAlign: 'right',
  },

  actionRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 14,
    borderBottomWidth: 1,
    borderBottomColor: '#f1f5f9',
  },
  actionIcon: { fontSize: 20, marginRight: 12 },
  actionText: { flex: 1, fontSize: 15, color: '#0f172a' },
  actionArrow: { fontSize: 22, color: '#cbd5e1' },

  logoutBtn: {
    backgroundColor: '#fee2e2',
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: 'center',
    marginTop: 8,
    marginBottom: 24,
    borderWidth: 1,
    borderColor: '#fecaca',
  },
  logoutText: { color: '#dc2626', fontSize: 15, fontWeight: '600' },

  footer: {
    textAlign: 'center',
    fontSize: 11,
    color: '#94a3b8',
    lineHeight: 16,
  },
})
