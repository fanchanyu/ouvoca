/**
 * Dashboard — 老闆視角儀表板
 */
import { useEffect, useState, useCallback } from 'react'
import {
  View, Text, ScrollView, RefreshControl, StyleSheet, ActivityIndicator,
} from 'react-native'
import { apiListParts, apiListWOs, apiBelowSafety, apiHealth } from '../../src/lib/api'

interface DashState {
  parts: number
  wos: number
  wosInProgress: number
  lowStock: Array<{ part_no: string; name: string; qty_available: number; safety_stock: number; shortage: number }>
  llmProvider: string
}

const fmt = (n: number) =>
  n.toLocaleString('zh-TW', { maximumFractionDigits: 0 })

export default function Dashboard() {
  const [data, setData] = useState<DashState | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setError(null)
    try {
      const [parts, wos, low, health] = await Promise.all([
        apiListParts(),
        apiListWOs(),
        apiBelowSafety(),
        apiHealth().catch(() => null),
      ])
      setData({
        parts: parts.length,
        wos: wos.length,
        wosInProgress: wos.filter(
          (w) => w.status === 'released' || w.status === 'in_progress',
        ).length,
        lowStock: low.slice(0, 5),
        llmProvider: health?.llm_provider || '—',
      })
    } catch (e) {
      setError(e instanceof Error ? e.message : '載入失敗 Load failed')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#2563eb" />
      </View>
    )
  }

  if (error) {
    return (
      <View style={styles.center}>
        <Text style={styles.errorText}>⚠️ {error}</Text>
      </View>
    )
  }

  return (
    <ScrollView
      style={styles.container}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load() }} />
      }
    >
      <Text style={styles.greeting}>{getGreeting()}</Text>
      <Text style={styles.title}>今日營運概覽</Text>

      {/* AI Summary */}
      <View style={styles.aiCard}>
        <Text style={styles.aiIcon}>🤖</Text>
        <View style={{ flex: 1 }}>
          <Text style={styles.aiLabel}>AI 智能摘要</Text>
          <Text style={styles.aiText}>
            {data && data.lowStock.length > 0
              ? `⚠️ ${data.lowStock.length} 項零件低於安全庫存（最缺：${data.lowStock[0].name}）`
              : '✓ 庫存水位正常'}
            {data && data.wosInProgress > 0 && `，生產中工單 ${data.wosInProgress} 張。`}
          </Text>
        </View>
      </View>

      {/* Stat Cards */}
      <View style={styles.statsRow}>
        <StatCard label="總零件" value={fmt(data?.parts || 0)} color="#2563eb" icon="📦" />
        <StatCard label="進行中" value={fmt(data?.wosInProgress || 0)} color="#16a34a" icon="🏭" />
      </View>
      <View style={styles.statsRow}>
        <StatCard label="總工單" value={fmt(data?.wos || 0)} color="#0891b2" icon="📋" />
        <StatCard
          label="庫存警示"
          value={fmt(data?.lowStock.length || 0)}
          color={data && data.lowStock.length > 0 ? '#dc2626' : '#64748b'}
          icon="⚠️"
        />
      </View>

      {/* Low Stock List */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>庫存警示</Text>
        {data && data.lowStock.length > 0 ? (
          data.lowStock.map((item) => (
            <View key={item.part_no} style={styles.alertRow}>
              <View style={{ flex: 1 }}>
                <Text style={styles.partNo}>{item.part_no}</Text>
                <Text style={styles.partName}>{item.name}</Text>
              </View>
              <View style={{ alignItems: 'flex-end' }}>
                <Text style={styles.qtyDanger}>{fmt(item.qty_available)}</Text>
                <Text style={styles.qtyLabel}>/ 安全 {fmt(item.safety_stock)}</Text>
              </View>
            </View>
          ))
        ) : (
          <Text style={styles.emptyText}>✅ 所有庫存正常</Text>
        )}
      </View>

      <View style={styles.footer}>
        <Text style={styles.footerText}>LLM Provider: {data?.llmProvider}</Text>
      </View>
    </ScrollView>
  )
}

function StatCard({ label, value, color, icon }: { label: string; value: string; color: string; icon: string }) {
  return (
    <View style={[styles.statCard, { borderLeftColor: color }]}>
      <View style={styles.statTop}>
        <Text style={styles.statLabel}>{label}</Text>
        <Text style={{ fontSize: 18 }}>{icon}</Text>
      </View>
      <Text style={[styles.statValue, { color }]}>{value}</Text>
    </View>
  )
}

function getGreeting(): string {
  const h = new Date().getHours()
  if (h < 11) return '早安 👋'
  if (h < 14) return '午安 👋'
  if (h < 18) return '下午好 👋'
  return '晚安 👋'
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f8fafc', padding: 16 },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  errorText: { color: '#dc2626', fontSize: 14 },
  greeting: { fontSize: 14, color: '#64748b' },
  title: { fontSize: 24, fontWeight: '700', color: '#0f172a', marginTop: 4, marginBottom: 16 },
  aiCard: {
    backgroundColor: '#dbeafe',
    borderColor: '#bfdbfe', borderWidth: 1,
    borderRadius: 14, padding: 14,
    flexDirection: 'row', gap: 12, alignItems: 'center',
    marginBottom: 16,
  },
  aiIcon: { fontSize: 28 },
  aiLabel: { fontSize: 11, fontWeight: '600', color: '#1d4ed8', textTransform: 'uppercase' },
  aiText: { fontSize: 14, color: '#1e3a8a', marginTop: 4, lineHeight: 20 },
  statsRow: { flexDirection: 'row', gap: 10, marginBottom: 10 },
  statCard: {
    flex: 1, backgroundColor: '#fff',
    borderRadius: 12, padding: 14,
    borderLeftWidth: 4,
    shadowColor: '#000', shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05, shadowRadius: 2, elevation: 1,
  },
  statTop: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  statLabel: { fontSize: 12, color: '#64748b' },
  statValue: { fontSize: 28, fontWeight: '700', marginTop: 4 },
  section: { marginTop: 16, backgroundColor: '#fff', borderRadius: 14, padding: 14 },
  sectionTitle: { fontSize: 16, fontWeight: '600', color: '#0f172a', marginBottom: 12 },
  alertRow: {
    flexDirection: 'row', justifyContent: 'space-between',
    paddingVertical: 8, borderBottomWidth: 1, borderBottomColor: '#f1f5f9',
  },
  partNo: { fontSize: 13, fontWeight: '600', color: '#0f172a', fontFamily: 'monospace' },
  partName: { fontSize: 11, color: '#64748b', marginTop: 2 },
  qtyDanger: { fontSize: 16, fontWeight: '700', color: '#dc2626' },
  qtyLabel: { fontSize: 10, color: '#94a3b8', marginTop: 2 },
  emptyText: { textAlign: 'center', color: '#64748b', paddingVertical: 20 },
  footer: { paddingVertical: 16, alignItems: 'center' },
  footerText: { fontSize: 11, color: '#94a3b8' },
})
