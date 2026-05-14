/**
 * Inventory — 庫存清單（含搜尋）
 */
import { useEffect, useState } from 'react'
import {
  View, Text, FlatList, TextInput, RefreshControl, StyleSheet, ActivityIndicator,
} from 'react-native'
import { apiListParts, type Part } from '../../src/lib/api'

export default function Inventory() {
  const [parts, setParts] = useState<Part[]>([])
  const [filtered, setFiltered] = useState<Part[]>([])
  const [keyword, setKeyword] = useState('')
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  async function load() {
    try {
      const data = await apiListParts()
      setParts(data)
      setFiltered(data)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => { load() }, [])

  useEffect(() => {
    if (!keyword) {
      setFiltered(parts)
    } else {
      const k = keyword.toLowerCase()
      setFiltered(parts.filter(p =>
        p.part_no.toLowerCase().includes(k) || p.name.toLowerCase().includes(k)
      ))
    }
  }, [keyword, parts])

  return (
    <View style={styles.container}>
      <View style={styles.searchBox}>
        <Text style={styles.searchIcon}>🔍</Text>
        <TextInput
          style={styles.searchInput}
          placeholder="搜尋料號或名稱 / Search part no. or name"
          value={keyword}
          onChangeText={setKeyword}
          placeholderTextColor="#94a3b8"
        />
      </View>

      {loading ? (
        <View style={styles.center}><ActivityIndicator color="#2563eb" /></View>
      ) : (
        <FlatList
          data={filtered}
          keyExtractor={(item) => item.id}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); load() }} />
          }
          ListHeaderComponent={
            <Text style={styles.count}>
              共 {filtered.length} / {parts.length} 個零件
            </Text>
          }
          ListEmptyComponent={
            <Text style={styles.empty}>無資料 / No data</Text>
          }
          renderItem={({ item }) => (
            <View style={styles.partCard}>
              <View style={{ flex: 1 }}>
                <Text style={styles.partNo}>{item.part_no}</Text>
                <Text style={styles.partName}>{item.name}</Text>
                <View style={styles.tags}>
                  <Tag label={item.category} color="#3b82f6" />
                  {!item.is_active && <Tag label="停用" color="#94a3b8" />}
                </View>
              </View>
              <View style={{ alignItems: 'flex-end' }}>
                <Text style={styles.cost}>${item.unit_cost.toFixed(2)}</Text>
                <Text style={styles.safetyLabel}>安全 {item.safety_stock}</Text>
              </View>
            </View>
          )}
        />
      )}
    </View>
  )
}

function Tag({ label, color }: { label: string; color: string }) {
  return (
    <View style={[styles.tag, { backgroundColor: `${color}20`, borderColor: color }]}>
      <Text style={[styles.tagText, { color }]}>{label}</Text>
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f8fafc' },
  searchBox: {
    flexDirection: 'row', alignItems: 'center',
    backgroundColor: '#fff', margin: 12, paddingHorizontal: 12,
    borderRadius: 10, borderWidth: 1, borderColor: '#e2e8f0',
  },
  searchIcon: { fontSize: 16 },
  searchInput: { flex: 1, paddingVertical: 12, paddingHorizontal: 8, fontSize: 15, color: '#0f172a' },
  count: { paddingHorizontal: 12, paddingBottom: 8, fontSize: 12, color: '#64748b' },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  empty: { textAlign: 'center', color: '#94a3b8', paddingVertical: 40 },
  partCard: {
    backgroundColor: '#fff', marginHorizontal: 12, marginBottom: 8,
    padding: 14, borderRadius: 12, flexDirection: 'row',
    shadowColor: '#000', shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05, shadowRadius: 2, elevation: 1,
  },
  partNo: { fontSize: 14, fontWeight: '700', color: '#0f172a', fontFamily: 'monospace' },
  partName: { fontSize: 13, color: '#475569', marginTop: 2 },
  tags: { flexDirection: 'row', gap: 6, marginTop: 6 },
  tag: { paddingHorizontal: 8, paddingVertical: 2, borderRadius: 8, borderWidth: 1 },
  tagText: { fontSize: 10, fontWeight: '600' },
  cost: { fontSize: 16, fontWeight: '700', color: '#0f172a' },
  safetyLabel: { fontSize: 10, color: '#64748b', marginTop: 2 },
})
