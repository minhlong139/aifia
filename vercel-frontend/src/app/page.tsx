'use client'

export default function HomePage() {
  return (
    <main className="min-h-screen bg-gray-50">
      <header className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-2xl">🏦</span>
            <h1 className="text-xl font-bold">AIFIA</h1>
            <span className="text-gray-500 text-sm ml-1">AI Financial Intelligence</span>
          </div>
          <div className="text-sm text-gray-500">
            Thị trường chứng khoán Việt Nam
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Market Overview */}
        <section className="mb-8">
          <h2 className="text-lg font-semibold mb-4">Tổng quan thị trường</h2>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {[
              { label: 'VN-Index', value: '---', change: '--' },
              { label: 'VN30', value: '---', change: '--' },
              { label: 'HNX-Index', value: '---', change: '--' },
              { label: 'UPCOM', value: '---', change: '--' },
            ].map((item) => (
              <div key={item.label} className="bg-white rounded-lg p-4 shadow-sm border">
                <div className="text-sm text-gray-500">{item.label}</div>
                <div className="text-2xl font-bold mt-1">{item.value}</div>
                <div className="text-sm mt-1">{item.change}</div>
              </div>
            ))}
          </div>
        </section>

        {/* Quick Actions */}
        <section className="mb-8">
          <div className="bg-white rounded-lg p-6 shadow-sm border">
            <h2 className="text-lg font-semibold mb-2">🚀 Bắt đầu</h2>
            <p className="text-gray-600 mb-4">
              Nhập mã cổ phiếu để xem phân tích AI chi tiết
            </p>
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="VD: FPT, VCB, VNM..."
                className="flex-1 px-4 py-2 border rounded-lg"
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    const val = (e.target as HTMLInputElement).value.trim()
                    if (val) window.location.href = `/company/${val.toUpperCase()}`
                  }
                }}
              />
              <button
                className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                onClick={() => {
                  const input = document.querySelector('input') as HTMLInputElement
                  if (input?.value) window.location.href = `/company/${input.value.toUpperCase()}`
                }}
              >
                Phân tích
              </button>
            </div>
          </div>
        </section>

        {/* Top Rated */}
        <section>
          <h2 className="text-lg font-semibold mb-4">🏆 Cổ phiếu được đánh giá cao</h2>
          <div className="bg-white rounded-lg shadow-sm border overflow-hidden">
            <div className="p-8 text-center text-gray-400">
              <div className="text-4xl mb-2">📊</div>
              <p>Dữ liệu sẽ hiển thị sau khi cấu hình Supabase</p>
              <p className="text-sm mt-2">
                Chạy crawl pipeline để thu thập dữ liệu trước
              </p>
            </div>
          </div>
        </section>
      </div>

      <footer className="border-t mt-12 py-6 text-center text-sm text-gray-400">
        <p>AIFIA - AI Financial Intelligence Assistant</p>
        <p className="mt-1">Dữ liệu từ Vnstock • Phân tích bởi AI</p>
      </footer>
    </main>
  )
}
