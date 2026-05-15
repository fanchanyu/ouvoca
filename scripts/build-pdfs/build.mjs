#!/usr/bin/env node
/**
 * LLM-ERP Customer-Facing Docs → PDF Builder
 *
 * 使用方式 / Usage:
 *   cd scripts/build-pdfs
 *   npm install
 *   npm run build
 *
 * 輸出 / Output: docs/pdf/*.pdf
 *
 * 特色 / Features:
 *   • Mermaid 圖自動預處理為 SVG（透過 @mermaid-js/mermaid-cli）
 *   • 中文字型 fallback 鏈
 *   • A4 排版 + 頁首頁尾 + 頁碼
 *   • 代碼塊長行自動折行
 */

import { mdToPdf } from 'md-to-pdf'
import { fileURLToPath } from 'url'
import { dirname, resolve, basename, join } from 'path'
import {
  existsSync, mkdirSync, readFileSync, writeFileSync,
  rmSync, mkdtempSync,
} from 'fs'
import { tmpdir } from 'os'
import { run as mmdcRun } from '@mermaid-js/mermaid-cli'

const __dirname = dirname(fileURLToPath(import.meta.url))
const ROOT = resolve(__dirname, '..', '..')
const DOCS = resolve(ROOT, 'docs')
const OUT  = resolve(DOCS, 'pdf')
const CSS  = resolve(__dirname, 'style.css')

if (!existsSync(OUT)) mkdirSync(OUT, { recursive: true })

// 共用 mermaid 臨時資料夾（每次 build 開新的）
const MERMAID_TMP = mkdtempSync(join(tmpdir(), 'llm-erp-mermaid-'))
console.log(`Mermaid temp dir: ${MERMAID_TMP}`)

// ───────────── 客戶面向文件清單 ─────────────
const DOCS_TO_BUILD = [
  // === 00 產品說明（給採購決策者）===
  { src: 'PRODUCT_OVERVIEW_ZH.md',       out: '00_產品說明書_中文.pdf',                    title: 'LLM-ERP 產品說明書' },
  { src: 'PRODUCT_OVERVIEW_EN.md',       out: '00_Product_Overview_EN.pdf',                title: 'LLM-ERP Product Overview' },

  // === 01-07 客戶/操作面向 ===
  { src: 'INSTALLATION_ZH.md',           out: '01_安裝指南_中文.pdf',                      title: 'LLM-ERP 安裝指南' },
  { src: 'INSTALLATION_EN.md',           out: '01_Installation_Guide_EN.pdf',              title: 'LLM-ERP Installation Guide' },
  { src: 'QUICK_START.md',               out: '02_快速入門_Quick_Start.pdf',               title: '快速入門 / Quick Start' },
  { src: 'USER_MANUAL_ZH.md',            out: '03_使用者操作手冊_中文.pdf',                title: 'LLM-ERP 使用者操作手冊' },
  { src: 'USER_MANUAL_EN.md',            out: '03_User_Manual_EN.pdf',                     title: 'LLM-ERP User Manual' },
  { src: 'NETWORK_DEPLOYMENT_ZH.md',     out: '05_網路部署規劃_中文.pdf',                  title: 'LLM-ERP 網路部署規劃' },
  { src: 'NETWORK_DEPLOYMENT_EN.md',     out: '05_Network_Deployment_EN.pdf',              title: 'LLM-ERP Network Deployment' },
  { src: 'SYSTEM_TOPOLOGY_ZH.md',        out: '06_系統架構流程拓樸_中文.pdf',              title: 'LLM-ERP 系統架構流程拓樸圖' },
  { src: 'SYSTEM_TOPOLOGY_EN.md',        out: '06_System_Architecture_Topology_EN.pdf',    title: 'LLM-ERP System Architecture & Topology' },
  { src: 'LLM_BENCHMARK_REPORT_ZH.md',   out: '07_LLM評比報告_中文.pdf',                   title: 'LLM 評比報告' },
  { src: 'LLM_BENCHMARK_REPORT_EN.md',   out: '07_LLM_Benchmark_Report_EN.pdf',            title: 'LLM Benchmark Report' },

  // === 08-12 v2.5 新增 ===
  { src: 'AGENT_CATALOG_ZH.md',          out: '08_AI助手目錄_中文.pdf',                    title: 'AI Agent 與 Tool 目錄' },
  { src: 'AGENT_CATALOG_EN.md',          out: '08_AI_Agent_Catalog_EN.pdf',                title: 'AI Agent & Tool Catalog' },

  { src: 'COMPLIANCE_TW_ZH.md',          out: '09_台灣合規對照表_中文.pdf',                title: '台灣合規對照表' },
  { src: 'COMPLIANCE_TW_EN.md',          out: '09_Taiwan_Compliance_EN.pdf',               title: 'Taiwan Compliance Reference' },

  { src: 'IMPLEMENTATION_PLAYBOOK_ZH.md',out: '10_導入實施手冊_中文.pdf',                  title: '導入實施手冊（顧問用）' },
  { src: 'IMPLEMENTATION_PLAYBOOK_EN.md',out: '10_Implementation_Playbook_EN.pdf',         title: 'Implementation Playbook' },

  { src: 'SUPPORT_RUNBOOK_ZH.md',        out: '11_支援運維手冊_中文.pdf',                  title: '支援運維手冊' },
  { src: 'SUPPORT_RUNBOOK_EN.md',        out: '11_Support_Runbook_EN.pdf',                 title: 'Support Runbook' },

  { src: 'BACKUP_RESTORE_SOP_ZH.md',     out: '12_備份還原SOP_中文.pdf',                   title: '備份還原 SOP' },
  { src: 'BACKUP_RESTORE_SOP_EN.md',     out: '12_Backup_Restore_SOP_EN.pdf',              title: 'Backup & Restore SOP' },

  // === 13-14 v2.6 新增（網路架構師視角）===
  { src: 'ARCHITECTURE_BLUEPRINT_ZH.md', out: '13_系統架構藍圖_中文.pdf',                  title: '系統架構藍圖' },
  { src: 'ARCHITECTURE_BLUEPRINT_EN.md', out: '13_Architecture_Blueprint_EN.pdf',          title: 'Architecture Blueprint' },
  { src: 'SECRETS_ROTATION_SOP_ZH.md',   out: '14_Secrets輪換SOP_中文.pdf',                title: 'Secrets 輪換 SOP' },
  { src: 'SECRETS_ROTATION_SOP_EN.md',   out: '14_Secrets_Rotation_SOP_EN.pdf',            title: 'Secrets Rotation SOP' },

  // === 15-16 對話式 ERP 北極星文件（v2.8）===
  { src: 'CONVERSATIONAL_ERP_DESIGN_ZH.md',     out: '15_對話式ERP架構_中文.pdf',           title: '對話式 ERP 架構設計' },
  { src: 'CONVERSATIONAL_ERP_DESIGN_EN.md',     out: '15_Conversational_ERP_Architecture_EN.pdf', title: 'Conversational ERP Architecture' },
  { src: 'CONVERSATIONAL_ERP_PHASE1_SPEC_ZH.md',out: '16_Phase1_實作Spec_中文.pdf',          title: 'Phase 1 實作 Spec' },
  { src: 'CONVERSATIONAL_ERP_PHASE1_SPEC_EN.md',out: '16_Phase1_Implementation_Spec_EN.pdf', title: 'Phase 1 Implementation Spec' },

  // === 17 v3.1 外部 DB 串接設計 ===
  { src: 'EXTERNAL_DB_INTEGRATION_DESIGN_ZH.md', out: '17_外部DB串接設計_中文.pdf',           title: '外部 DB 串接設計' },
  { src: 'EXTERNAL_DB_INTEGRATION_DESIGN_EN.md', out: '17_External_DB_Integration_Design_EN.pdf', title: 'External DB Integration Design' },

  // === 18 v3.5 Sales killer moments 一頁紙 ===
  { src: 'SALES_KILLER_MOMENTS_ZH.md', out: '18_業務demo一頁紙_中文.pdf',                title: '業務 demo 一頁紙 — 9 killer moments' },
  { src: 'SALES_KILLER_MOMENTS_EN.md', out: '18_Sales_Killer_Moments_EN.pdf',          title: 'Sales Demo One-Pager — 9 killer moments' },
]

// ───────────── Mermaid 預處理 ─────────────
// 把 markdown 中的 ```mermaid``` 區塊轉成 SVG 並替換為 <img>
let mermaidCounter = 0

async function preprocessMermaid(markdown, sourceLabel) {
  const re = /```mermaid\n([\s\S]+?)\n```/g
  const blocks = [...markdown.matchAll(re)]
  if (blocks.length === 0) return markdown

  console.log(`    ↳ ${blocks.length} mermaid block(s) detected, rendering to SVG...`)

  let processed = markdown
  for (const m of blocks) {
    const code = m[1].trim()
    mermaidCounter += 1
    const mmdPath = join(MERMAID_TMP, `m${mermaidCounter}.mmd`)
    const svgPath = join(MERMAID_TMP, `m${mermaidCounter}.svg`)
    writeFileSync(mmdPath, code, 'utf-8')

    try {
      await mmdcRun(mmdPath, svgPath, {
        puppeteerConfig: {
          args: ['--no-sandbox', '--disable-setuid-sandbox'],
        },
        parseMMDOptions: {
          mermaidConfig: {
            theme: 'default',
            themeVariables: {
              fontFamily: '"Microsoft JhengHei","PingFang TC","Noto Sans CJK TC",sans-serif',
            },
            flowchart: { useMaxWidth: true, htmlLabels: true, curve: 'basis' },
            sequence:  { useMaxWidth: true, showSequenceNumbers: false },
            gantt:     { useMaxWidth: true },
          },
        },
      })

      // 讀回 SVG 並直接內嵌（避免 Puppeteer file:// 安全限制）
      let svgContent = readFileSync(svgPath, 'utf-8')
      // 移除 XML declaration 和 DOCTYPE（內嵌時不能有）
      svgContent = svgContent
        .replace(/<\?xml[^?]*\?>/g, '')
        .replace(/<!DOCTYPE[^>]*>/g, '')
        .trim()
      const replacement = `\n<div class="mermaid-wrap">\n${svgContent}\n</div>\n`
      processed = processed.replace(m[0], replacement)
    } catch (e) {
      console.error(`    ⚠️  mermaid render failed (${sourceLabel} block #${mermaidCounter}): ${e.message}`)
      // 渲染失敗就保留原 code block（至少不會整段消失）
    }
  }
  return processed
}

// ───────────── PDF 共用選項 ─────────────
function pdfOptionsFor(title) {
  return {
    stylesheet: [CSS],
    pdf_options: {
      format: 'A4',
      margin: { top: '20mm', right: '16mm', bottom: '22mm', left: '16mm' },
      printBackground: true,
      displayHeaderFooter: true,
      headerTemplate: `
        <div style="font-size:8pt; color:#94a3b8; width:100%; padding:0 16mm;
                    display:flex; justify-content:space-between;">
          <span>${title}</span>
          <span>LLM-ERP · AI-Native ERP</span>
        </div>`,
      footerTemplate: `
        <div style="font-size:8pt; color:#94a3b8; width:100%; padding:0 16mm;
                    display:flex; justify-content:space-between;">
          <span>© 2026 LLM-ERP Project</span>
          <span>第 <span class="pageNumber"></span> / <span class="totalPages"></span> 頁</span>
        </div>`,
    },
    launch_options: {
      args: ['--no-sandbox', '--disable-setuid-sandbox'],
    },
    marked_options: {
      gfm: true,
      breaks: false,
    },
    basedir: DOCS,
  }
}

// ───────────── 跑單檔 ─────────────
async function buildOne({ src, out, title }) {
  const srcPath = resolve(DOCS, src)
  const outPath = resolve(OUT, out)

  if (!existsSync(srcPath)) {
    console.log(`  ⚠️  Skip (not found): ${src}`)
    return { skipped: true }
  }

  let content = readFileSync(srcPath, 'utf-8')

  // 補頂層 H1（若無）
  if (!/^#\s/m.test(content.split('\n').slice(0, 5).join('\n'))) {
    content = `# ${title}\n\n${content}`
  }

  // 預處理 Mermaid
  content = await preprocessMermaid(content, basename(src))

  try {
    await mdToPdf(
      { content },
      { ...pdfOptionsFor(title), dest: outPath },
    )
    return { ok: true, outPath }
  } catch (e) {
    console.error(`  ❌ FAILED: ${src} → ${e.message}`)
    return { failed: true, err: e.message }
  }
}

// ───────────── Main ─────────────
console.log('\n📚 LLM-ERP PDF Builder')
console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
console.log(`輸入 / Input : ${DOCS}`)
console.log(`輸出 / Output: ${OUT}`)
console.log(`樣式 / Style : ${CSS}`)
console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n')

let ok = 0, skipped = 0, failed = 0
const t0 = Date.now()

for (const doc of DOCS_TO_BUILD) {
  process.stdout.write(`▶ ${doc.out.padEnd(46)}`)
  const r = await buildOne(doc)
  if (r.ok) { console.log(' ✅'); ok++ }
  else if (r.skipped) { skipped++ }
  else { failed++ }
}

// 清理 mermaid 臨時檔
try { rmSync(MERMAID_TMP, { recursive: true, force: true }) } catch {}

const dt = ((Date.now() - t0) / 1000).toFixed(1)
console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
console.log(`✅ 成功 / OK     : ${ok}`)
console.log(`⚠️  跳過 / Skipped: ${skipped}`)
console.log(`❌ 失敗 / Failed : ${failed}`)
console.log(`⏱  耗時 / Time   : ${dt}s`)
console.log(`📂 輸出位置 / Output: ${OUT}`)
console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n')

if (failed > 0) process.exit(1)
