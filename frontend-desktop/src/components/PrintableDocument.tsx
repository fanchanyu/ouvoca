/**
 * PrintableDocument — 通用單據列印 modal（Sprint O v3.21）
 *
 * 對標鼎新 / 正航 / SAP B1：每張單據（PO / SO / 出貨單 / 發票）都要能印出
 * 給供應商 / 客戶 / 內部存檔。
 *
 * 使用方式：
 *   <PrintableDocument
 *     title="採購單 PO-2026-0042"
 *     onClose={() => setShowPrint(null)}
 *   >
 *     // 你的單據 layout
 *   </PrintableDocument>
 *
 * 設計：
 *  - Modal 容器 + 「🖨 列印 / 存 PDF」按鈕
 *  - @media print CSS：隱藏 sidebar / header / 自己的關閉按鈕
 *  - 列印時純白背景、A4 大小、中文字型 fallback
 *  - 使用者按列印 → 瀏覽器原生 print dialog → 「另存為 PDF」
 */
import { useEffect } from 'react'

interface Props {
  title: string
  onClose: () => void
  children: React.ReactNode
}

export default function PrintableDocument({ title, onClose, children }: Props) {
  // ESC 關閉
  useEffect(() => {
    const h = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [onClose])

  function doPrint() { window.print() }

  return (
    <>
      {/* 列印時用的 CSS — 把非 print-area 全藏掉 */}
      <style>{`
        @media print {
          body * { visibility: hidden; }
          .ouvoca-print-area, .ouvoca-print-area * { visibility: visible; }
          .ouvoca-print-area {
            position: absolute; top: 0; left: 0; width: 100%;
            background: white; padding: 20mm 15mm;
          }
          .no-print { display: none !important; }
          @page { size: A4; margin: 0; }
        }
      `}</style>

      {/* Modal backdrop */}
      <div className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm flex items-start justify-center p-4 overflow-y-auto no-print">
        <div className="bg-white rounded-2xl shadow-2xl max-w-4xl w-full my-6">
          {/* Toolbar — 列印時隱藏 */}
          <div className="flex items-center justify-between p-3 border-b no-print">
            <h2 className="font-semibold text-gray-800">{title}</h2>
            <div className="flex gap-2">
              <button onClick={doPrint}
                className="px-3 py-1.5 bg-blue-600 text-white rounded text-sm hover:bg-blue-700">
                🖨 列印 / 存 PDF
              </button>
              <button onClick={onClose}
                className="px-3 py-1.5 text-gray-500 hover:bg-gray-100 rounded text-sm">
                ✕ 關閉
              </button>
            </div>
          </div>

          {/* 列印區域 — 列印時只剩這 */}
          <div className="ouvoca-print-area p-6">
            {children}
          </div>

          {/* 列印提示 — 列印時隱藏 */}
          <div className="border-t bg-gray-50 px-3 py-2 text-xs text-gray-500 text-center no-print">
            💡 按「🖨 列印」→ 在瀏覽器列印對話框選「另存為 PDF」即可存檔給客戶 / 供應商
          </div>
        </div>
      </div>
    </>
  )
}

// ────────────────────────────────────────────────────────────
// 通用單據樣板（給 PO / SO / 出貨單共用的 header + footer）
// ────────────────────────────────────────────────────────────
interface DocHeaderProps {
  docType: string         // 「採購單」/「銷售單」/「出貨單」
  docNo: string
  date: string
  companyName?: string    // 預設 Ouvoca 演示公司
}

export function DocHeader({ docType, docNo, date, companyName = '示範公司股份有限公司' }: DocHeaderProps) {
  return (
    <div className="border-b pb-4 mb-4">
      <div className="flex justify-between items-start">
        <div>
          <div className="text-xl font-bold">{companyName}</div>
          <div className="text-xs text-gray-500 mt-1">{docType}</div>
        </div>
        <div className="text-right">
          <div className="text-2xl font-bold text-blue-700">{docType}</div>
          <div className="text-xs text-gray-500 mt-1">No. <span className="font-mono">{docNo}</span></div>
          <div className="text-xs text-gray-500">日期：{date}</div>
        </div>
      </div>
    </div>
  )
}

export function DocFooter({ note }: { note?: string }) {
  return (
    <div className="border-t pt-4 mt-4">
      {note && <div className="text-xs text-gray-600 mb-3">📝 備註：{note}</div>}
      <div className="grid grid-cols-3 gap-4 text-xs">
        <div>
          <div className="text-gray-500 mb-1">承辦人</div>
          <div className="border-t border-gray-400 mt-12"></div>
        </div>
        <div>
          <div className="text-gray-500 mb-1">主管簽核</div>
          <div className="border-t border-gray-400 mt-12"></div>
        </div>
        <div>
          <div className="text-gray-500 mb-1">客戶 / 供應商簽收</div>
          <div className="border-t border-gray-400 mt-12"></div>
        </div>
      </div>
      <div className="text-center text-xs text-gray-400 mt-6">
        — 本單據由 Ouvoca 開立 · https://github.com/fanchanyu/ouvoca —
      </div>
    </div>
  )
}
