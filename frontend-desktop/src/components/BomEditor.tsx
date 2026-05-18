/**
 * BomEditor — 產品「做法 (Recipe)」編輯（Sprint Q v3.23 / Sprint R 改名 v3.24）
 *
 * **erpilot 原創詞**：對手鼎新/SAP 叫 "BOM / 物料表"，我們叫「**做法 / Recipe**」。
 * 像食譜，小白一看就懂「這產品怎麼做」。
 *
 * 製造業核心：每個產品的「做法」= 該產品由哪些料件組成 + 用量。
 * WO release 業務規則需要做法，沒這個 release 會失敗。
 *
 * UI：modal 內顯示 (product → 元件清單)，可加新行 (component_part_id + qty_per)。
 * Backend 仍叫 BOMItem (向後相容)，UI 全 rebrand 為「做法 / Recipe」。
 */
import { useEffect, useState } from 'react'
import {
  apiListBOM, apiCreateBOMItem, apiListParts,
  type BOMItem, type Part, type Product,
} from '../lib/api'

interface Props {
  product: Product
  onClose: () => void
}

export default function BomEditor({ product, onClose }: Props) {
  const [items, setItems] = useState<BOMItem[]>([])
  const [parts, setParts] = useState<Part[]>([])
  const [loading, setLoading] = useState(true)
  const [adding, setAdding] = useState(false)
  const [draft, setDraft] = useState({ component_part_id: '', qty_per: 1, unit: 'pcs' })
  const [err, setErr] = useState<string | null>(null)

  async function load() {
    setLoading(true); setErr(null)
    try {
      const [bom, p] = await Promise.all([
        apiListBOM(product.id).catch(() => [] as BOMItem[]),
        apiListParts().catch(() => [] as Part[]),
      ])
      setItems(bom); setParts(p)
    } catch (e: unknown) { setErr(e instanceof Error ? e.message : '載入失敗') }
    finally { setLoading(false) }
  }

  useEffect(() => { void load() }, [product.id])

  async function addItem() {
    if (!draft.component_part_id || draft.qty_per <= 0) {
      setErr('料件 + 用量必填'); return
    }
    setErr(null)
    try {
      await apiCreateBOMItem({
        product_id: product.id,
        component_part_id: draft.component_part_id,
        qty_per: draft.qty_per,
        unit: draft.unit,
      })
      setDraft({ component_part_id: '', qty_per: 1, unit: 'pcs' })
      setAdding(false)
      await load()
    } catch (e: unknown) { setErr(e instanceof Error ? e.message : '新增失敗') }
  }

  const partLabel = (id: string) => {
    const p = parts.find(x => x.id === id)
    return p ? `${p.part_no} ${p.name}` : id.slice(0, 8)
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-start justify-center p-4 overflow-y-auto"
      onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-2xl max-w-3xl w-full my-6" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between p-3 border-b">
          <div>
            <h2 className="font-semibold">📖 產品做法 (Recipe)</h2>
            <p className="text-xs text-gray-500 mt-0.5">產品：{product.product_no} {product.name}</p>
          </div>
          <button onClick={onClose} className="text-gray-500 hover:bg-gray-100 px-2 py-1 rounded text-sm">✕</button>
        </div>

        <div className="p-4">
          {err && <div className="bg-red-50 text-red-700 px-3 py-2 rounded mb-3 text-sm">{err}</div>}

          <div className="flex justify-between items-center mb-3">
            <p className="text-sm text-gray-600">
              <strong>{items.length}</strong> 個元件
              {items.length === 0 && <span className="text-amber-600 ml-2">⚠️ 還沒填做法，工單將無法 release</span>}
            </p>
            <button onClick={() => setAdding(a => !a)}
              className="px-3 py-1.5 bg-blue-600 text-white rounded text-sm hover:bg-blue-700">
              {adding ? '取消' : '➕ 加元件'}
            </button>
          </div>

          {adding && (
            <div className="bg-blue-50 rounded p-3 mb-3">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
                <select className="border rounded px-2 py-1.5 text-sm"
                  value={draft.component_part_id}
                  onChange={(e) => setDraft({ ...draft, component_part_id: e.target.value })}>
                  <option value="">選元件料件*</option>
                  {parts.map(p => (
                    <option key={p.id} value={p.id}>{p.part_no} {p.name}</option>
                  ))}
                </select>
                <input type="number" className="border rounded px-2 py-1.5 text-sm"
                  placeholder="用量 (每個產品需要 N 個)*" min="0.001" step="0.001"
                  value={draft.qty_per || ''}
                  onChange={(e) => setDraft({ ...draft, qty_per: Number(e.target.value) })} />
                <button onClick={addItem}
                  className="px-3 py-1.5 bg-emerald-600 text-white rounded text-sm hover:bg-emerald-700">
                  ✓ 加進 BOM
                </button>
              </div>
              {parts.length === 0 && (
                <p className="text-xs text-amber-600 mt-2">
                  ⚠️ 還沒料件？先去庫存頁新增料件。
                </p>
              )}
            </div>
          )}

          {loading ? (
            <div className="text-center text-gray-400 py-12">載入中…</div>
          ) : items.length === 0 ? (
            <div className="text-center py-12">
              <div className="text-4xl mb-2">📖</div>
              <p className="text-sm text-gray-600">這個產品還沒有「做法」(Recipe)</p>
              <p className="text-xs text-gray-400 mt-1">
                做法 = 「產品由哪些料件組成 + 每樣多少個」，就像食譜<br/>
                例：M6 螺絲 1 個 + M6 螺帽 1 個 = 1 套螺絲組
              </p>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="text-left p-2">元件 / 料件</th>
                  <th className="text-right p-2">用量 (per 產品)</th>
                  <th className="text-center p-2">單位</th>
                </tr>
              </thead>
              <tbody>
                {items.map(it => (
                  <tr key={it.id} className="border-t">
                    <td className="p-2">{partLabel(it.component_part_id)}</td>
                    <td className="p-2 text-right font-mono">{it.qty_per}</td>
                    <td className="p-2 text-center text-xs text-gray-500">{it.unit || 'pcs'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <div className="border-t bg-gray-50 px-3 py-2 text-xs text-gray-500 text-center">
          💡 「做法」設好後該產品的工單可以 release。MRP 也會自動算出每張工單需要拉多少料。
        </div>
      </div>
    </div>
  )
}
