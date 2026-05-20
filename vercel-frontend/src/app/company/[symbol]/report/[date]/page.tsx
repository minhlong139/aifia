import { getReport } from '@/lib/reports'
import Link from 'next/link'

// Simple markdown-to-JSX renderer
function renderMarkdown(md: string): React.ReactNode[] {
  const lines = md.split('\n')
  const elements: React.ReactNode[] = []
  let i = 0
  let inTable = false
  let tableRows: string[][] = []
  let tableAligns: string[] = []

  function flushTable() {
    if (tableRows.length === 0) return
    const headers = tableRows[0]
    const body = tableRows.slice(1)
    elements.push(
      <div key={`tbl-${elements.length}`} className="overflow-x-auto my-4">
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="border-b-2 border-gray-300">
              {headers.map((h, hi) => (
                <th key={hi} className={`py-2 px-3 text-left font-semibold text-gray-700 ${tableAligns[hi] === 'right' ? 'text-right' : ''}`}>
                  {inlineRender(h)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {body.map((row, ri) => (
              <tr key={ri} className="border-b border-gray-200 hover:bg-gray-50">
                {row.map((cell, ci) => (
                  <td key={ci} className={`py-2 px-3 ${tableAligns[ci] === 'right' ? 'text-right font-medium tabular-nums' : ''}`}>
                    {inlineRender(cell)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )
    tableRows = []
    tableAligns = []
    inTable = false
  }

  function flushParagraph(buf: string[]) {
    if (buf.length === 0) return
    const text = buf.join(' ')
    elements.push(
      <p key={`p-${elements.length}`} className="my-2 text-gray-800 leading-relaxed">
        {inlineRender(text)}
      </p>
    )
    buf.length = 0
  }

  let paraBuf: string[] = []
  let inCodeBlock = false
  let codeBuf: string[] = []
  let codeLang = ''

  for (i = 0; i < lines.length; i++) {
    const raw = lines[i]
    const line = raw.trim()

    // Code blocks
    if (line.startsWith('```')) {
      if (inCodeBlock) {
        elements.push(
          <pre key={`code-${elements.length}`} className="bg-gray-900 text-green-400 p-4 rounded-lg my-4 overflow-x-auto text-xs">
            <code>{codeBuf.join('\n')}</code>
          </pre>
        )
        codeBuf = []
        inCodeBlock = false
      } else {
        flushTable()
        flushParagraph(paraBuf)
        codeLang = line.slice(3).trim()
        inCodeBlock = true
      }
      continue
    }
    if (inCodeBlock) { codeBuf.push(raw); continue }

    // Separator
    if (line === '---') {
      flushTable()
      flushParagraph(paraBuf)
      elements.push(<hr key={`hr-${elements.length}`} className="my-6 border-gray-300" />)
      continue
    }

    // Tables
    if (line.startsWith('|')) {
      if (!inTable) {
        flushParagraph(paraBuf)
        inTable = true
        tableRows = []
        tableAligns = []
      }
      const cells = line.split('|').filter((_, ci, arr) => ci > 0 && ci < arr.length - 1).map(c => c.trim())
      // Check for alignment row
      if (cells.every(c => /^:?-+:?$/.test(c))) {
        tableAligns = cells.map(c => {
          if (c.startsWith(':') && c.endsWith(':')) return 'center'
          if (c.endsWith(':')) return 'right'
          return 'left'
        })
        continue
      }
      tableRows.push(cells)
      continue
    } else if (inTable) {
      flushTable()
    }

    // Headings
    const headingMatch = line.match(/^(#{1,6})\s+(.+)/)
    if (headingMatch) {
      flushParagraph(paraBuf)
      const level = headingMatch[1].length
      const text = headingMatch[2]
      const sizes = ['text-2xl', 'text-xl', 'text-lg', 'text-base', 'text-sm', 'text-xs']
      const margins = ['mt-8 mb-4', 'mt-6 mb-3', 'mt-5 mb-2', 'mt-4 mb-2', 'mt-3 mb-1', 'mt-2 mb-1']
      elements.push(
        React.createElement(`h${level}` as any, {
          key: `h-${elements.length}`,
          className: `font-bold text-gray-900 ${sizes[level - 1]} ${margins[level - 1]}`
        }, inlineRender(text))
      )
      continue
    }

    // Blockquote
    if (line.startsWith('>')) {
      flushParagraph(paraBuf)
      const quoteText = line.replace(/^>\s*/, '')
      elements.push(
        <blockquote key={`bq-${elements.length}`} className="border-l-4 border-blue-400 bg-blue-50 pl-4 py-2 my-3 rounded-r text-sm text-gray-700">
          {inlineRender(quoteText)}
        </blockquote>
      )
      continue
    }

    // Empty line → flush paragraph
    if (line === '') {
      flushParagraph(paraBuf)
      continue
    }

    // Regular text
    paraBuf.push(line)
  }

  flushTable()
  flushParagraph(paraBuf)

  return elements
}

function inlineRender(text: string): React.ReactNode {
  // Bold: **text**
  const parts = text.split(/(\*\*[^*]+\*\*)/g)
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={i} className="font-bold text-gray-900">{part.slice(2, -2)}</strong>
    }
    // Emoji highlight
    return <span key={i}>{part}</span>
  })
}

export default async function ReportPage({
  params,
}: {
  params: Promise<{ symbol: string; date: string }>
}) {
  const { symbol, date } = await params
  const report = getReport(symbol.toUpperCase(), date)

  if (!report) {
    return (
      <main className="min-h-screen bg-gray-50 p-8">
        <div className="max-w-4xl mx-auto text-center mt-20">
          <div className="text-6xl mb-4">📄</div>
          <h1 className="text-2xl font-bold mb-2">Không tìm thấy báo cáo</h1>
          <p className="text-gray-500 mb-4">{symbol} · {date}</p>
          <Link href={`/company/${symbol}`} className="text-blue-600 hover:underline">
            ← Quay lại {symbol}
          </Link>
        </div>
      </main>
    )
  }

  const dateDisplay = date.split('-').reverse().join('/')

  return (
    <main className="min-h-screen bg-gray-50">
      <header className="bg-white border-b sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between">
          <Link href={`/company/${symbol}`} className="text-blue-600 text-sm hover:underline">
            ← {symbol}
          </Link>
          <Link href="/" className="text-gray-400 text-sm hover:text-gray-600">Dashboard</Link>
        </div>
      </header>

      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="bg-white rounded-xl shadow-sm border p-6 md:p-8">
          <article className="prose prose-sm max-w-none text-gray-800">
            {renderMarkdown(report)}
          </article>

          <div className="mt-8 pt-6 border-t border-gray-200 text-center text-xs text-gray-400">
            AIFIA — AI Financial Intelligence Assistant · Báo cáo tạo ngày {dateDisplay}
          </div>
        </div>
      </div>
    </main>
  )
}

// Import for JSX
import React from 'react'
