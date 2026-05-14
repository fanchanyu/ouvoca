/**
 * Scan — QR Code 掃描頁
 * 用於：盤點 / 收料 / 外協回報
 */
import { useState, useEffect } from 'react'
import {
  View, Text, TouchableOpacity, StyleSheet, Alert, Linking,
} from 'react-native'
import { BarCodeScanner } from 'expo-barcode-scanner'

export default function Scan() {
  const [hasPermission, setHasPermission] = useState<boolean | null>(null)
  const [scanned, setScanned] = useState(false)
  const [data, setData] = useState<string | null>(null)

  useEffect(() => {
    BarCodeScanner.requestPermissionsAsync().then(({ status }) => {
      setHasPermission(status === 'granted')
    })
  }, [])

  function handleScan({ type, data }: { type: string; data: string }) {
    setScanned(true)
    setData(data)
    Alert.alert(
      '掃描成功 / Scanned',
      `類型 Type: ${type}\n內容 Data: ${data}`,
      [
        { text: '再掃 / Scan again', onPress: () => { setScanned(false); setData(null) } },
        { text: '完成 / Done' },
      ],
    )
  }

  if (hasPermission === null) {
    return (
      <View style={styles.center}>
        <Text>請求相機權限中... / Requesting camera permission...</Text>
      </View>
    )
  }

  if (!hasPermission) {
    return (
      <View style={styles.center}>
        <Text style={styles.title}>📷 沒有相機權限</Text>
        <Text style={styles.subtitle}>需要相機才能掃描 QR Code</Text>
        <TouchableOpacity
          style={styles.btn}
          onPress={() => Linking.openSettings()}
        >
          <Text style={styles.btnText}>前往設定開啟權限</Text>
        </TouchableOpacity>
      </View>
    )
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>掃描 QR Code</Text>
        <Text style={styles.subtitle}>對準 QR 自動辨識 / Auto-scan QR codes</Text>
      </View>

      <View style={styles.scannerContainer}>
        <BarCodeScanner
          onBarCodeScanned={scanned ? undefined : handleScan}
          style={styles.scanner}
        />
        <View style={styles.overlay}>
          <View style={styles.targetBox} />
        </View>
      </View>

      <View style={styles.instructions}>
        <Text style={styles.instructionTitle}>支援的使用情境：</Text>
        <Text style={styles.instruction}>📦 盤點：對準儲位 QR</Text>
        <Text style={styles.instruction}>🚚 收料：對準 PO 條碼</Text>
        <Text style={styles.instruction}>🔗 外協回報：對準派工單 QR</Text>
        <Text style={styles.instruction}>🏭 報工：對準工單 QR</Text>
      </View>

      {scanned && (
        <TouchableOpacity
          style={styles.btn}
          onPress={() => { setScanned(false); setData(null) }}
        >
          <Text style={styles.btnText}>↻ 再次掃描 / Scan again</Text>
        </TouchableOpacity>
      )}
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#000' },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', padding: 30, backgroundColor: '#f8fafc' },
  title: { fontSize: 18, fontWeight: '700', color: '#fff', marginBottom: 4, textAlign: 'center' },
  subtitle: { fontSize: 12, color: '#cbd5e1', textAlign: 'center' },
  header: { padding: 16, backgroundColor: 'rgba(15,23,42,0.9)' },
  scannerContainer: { flex: 1, position: 'relative' },
  scanner: { ...StyleSheet.absoluteFillObject },
  overlay: { ...StyleSheet.absoluteFillObject, justifyContent: 'center', alignItems: 'center' },
  targetBox: {
    width: 250, height: 250, borderColor: '#2563eb',
    borderWidth: 3, borderRadius: 24,
    backgroundColor: 'rgba(37,99,235,0.05)',
  },
  instructions: {
    padding: 16, backgroundColor: 'rgba(15,23,42,0.9)',
  },
  instructionTitle: { fontSize: 13, fontWeight: '600', color: '#fff', marginBottom: 8 },
  instruction: { fontSize: 12, color: '#cbd5e1', marginBottom: 4 },
  btn: {
    backgroundColor: '#2563eb', margin: 16,
    padding: 14, borderRadius: 10, alignItems: 'center',
  },
  btnText: { color: '#fff', fontSize: 15, fontWeight: '600' },
})
