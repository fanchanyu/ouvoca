/**
 * AI Chat — 自然語言助手
 */
import { useState, useRef } from 'react'
import {
  View, Text, TextInput, TouchableOpacity, ScrollView,
  KeyboardAvoidingView, Platform, StyleSheet, ActivityIndicator,
} from 'react-native'
import { apiChat } from '../../src/lib/api'

interface Msg {
  role: 'user' | 'assistant'
  content: string
  agent?: string
}

const SUGGESTIONS = [
  '列出庫存最低 5 個零件',
  '今天工廠營運狀況',
  '最近進行中的工單',
  '幫我查 M6 螺絲庫存',
]

export default function Chat() {
  const [messages, setMessages] = useState<Msg[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const sessionId = useRef(`mob-${Date.now()}`)
  const scrollRef = useRef<ScrollView>(null)

  async function send(text?: string) {
    const q = (text || input).trim()
    if (!q || loading) return

    setMessages((prev) => [...prev, { role: 'user', content: q }])
    setInput('')
    setLoading(true)

    try {
      const r = await apiChat(q, sessionId.current)
      setMessages((prev) => [...prev, {
        role: 'assistant', content: r.reply || '(無回應)', agent: r.agent,
      }])
    } catch (e) {
      setMessages((prev) => [...prev, {
        role: 'assistant',
        content: `❌ ${e instanceof Error ? e.message : '連線錯誤 / Connection error'}`,
      }])
    } finally {
      setLoading(false)
      setTimeout(() => scrollRef.current?.scrollToEnd({ animated: true }), 100)
    }
  }

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      keyboardVerticalOffset={Platform.OS === 'ios' ? 90 : 0}
    >
      <ScrollView
        ref={scrollRef}
        style={styles.scroll}
        contentContainerStyle={styles.scrollContent}
      >
        {messages.length === 0 && (
          <View style={styles.welcome}>
            <Text style={styles.welcomeIcon}>🤖</Text>
            <Text style={styles.welcomeText}>
              向 AI 助手詢問任何 ERP 問題{'\n'}Ask anything about your ERP
            </Text>
            <View style={styles.suggestions}>
              {SUGGESTIONS.map((s) => (
                <TouchableOpacity
                  key={s}
                  style={styles.suggBtn}
                  onPress={() => send(s)}
                >
                  <Text style={styles.suggText}>{s}</Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>
        )}

        {messages.map((m, i) => (
          <View
            key={i}
            style={[
              styles.msgRow,
              m.role === 'user' ? styles.msgRowUser : styles.msgRowAI,
            ]}
          >
            <View
              style={[
                styles.msgBubble,
                m.role === 'user' ? styles.bubbleUser : styles.bubbleAI,
              ]}
            >
              <Text style={m.role === 'user' ? styles.textUser : styles.textAI}>
                {m.content}
              </Text>
            </View>
            {m.agent && m.role === 'assistant' && (
              <Text style={styles.agentLabel}>→ {m.agent}</Text>
            )}
          </View>
        ))}

        {loading && (
          <View style={styles.msgRowAI}>
            <View style={styles.bubbleAI}>
              <ActivityIndicator size="small" color="#2563eb" />
            </View>
          </View>
        )}
      </ScrollView>

      <View style={styles.inputBar}>
        <TextInput
          style={styles.input}
          value={input}
          onChangeText={setInput}
          placeholder="輸入問題... / Type a question..."
          placeholderTextColor="#94a3b8"
          multiline
          onSubmitEditing={() => send()}
        />
        <TouchableOpacity
          style={[styles.sendBtn, (!input.trim() || loading) && styles.sendBtnDisabled]}
          onPress={() => send()}
          disabled={!input.trim() || loading}
        >
          <Text style={styles.sendBtnText}>↑</Text>
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f8fafc' },
  scroll: { flex: 1 },
  scrollContent: { padding: 12, paddingBottom: 20 },
  welcome: { alignItems: 'center', marginTop: 40 },
  welcomeIcon: { fontSize: 48, marginBottom: 12 },
  welcomeText: { fontSize: 14, color: '#64748b', textAlign: 'center', lineHeight: 20, marginBottom: 24 },
  suggestions: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, justifyContent: 'center', paddingHorizontal: 16 },
  suggBtn: {
    backgroundColor: '#fff', paddingVertical: 8, paddingHorizontal: 14,
    borderRadius: 18, borderWidth: 1, borderColor: '#e2e8f0',
  },
  suggText: { fontSize: 12, color: '#475569' },
  msgRow: { marginVertical: 6 },
  msgRowUser: { alignItems: 'flex-end' },
  msgRowAI: { alignItems: 'flex-start' },
  msgBubble: { maxWidth: '85%', padding: 12, borderRadius: 16 },
  bubbleUser: { backgroundColor: '#2563eb', borderBottomRightRadius: 4 },
  bubbleAI: { backgroundColor: '#fff', borderBottomLeftRadius: 4, borderWidth: 1, borderColor: '#e2e8f0' },
  textUser: { color: '#fff', fontSize: 14, lineHeight: 20 },
  textAI: { color: '#0f172a', fontSize: 14, lineHeight: 20 },
  agentLabel: { fontSize: 10, color: '#94a3b8', marginTop: 2, marginLeft: 4 },
  inputBar: {
    flexDirection: 'row', alignItems: 'center', padding: 8,
    borderTopWidth: 1, borderTopColor: '#e2e8f0', backgroundColor: '#fff',
  },
  input: {
    flex: 1, paddingHorizontal: 14, paddingVertical: 10,
    backgroundColor: '#f1f5f9', borderRadius: 22, fontSize: 14,
    color: '#0f172a', maxHeight: 100,
  },
  sendBtn: {
    width: 40, height: 40, borderRadius: 20,
    backgroundColor: '#2563eb', marginLeft: 8,
    justifyContent: 'center', alignItems: 'center',
  },
  sendBtnDisabled: { backgroundColor: '#cbd5e1' },
  sendBtnText: { color: '#fff', fontSize: 22, fontWeight: '600' },
})
