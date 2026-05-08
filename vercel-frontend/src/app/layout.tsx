import type { Metadata } from "next"
import "./globals.css"

export const metadata: Metadata = {
  title: "AIFIA - AI Financial Intelligence Assistant",
  description: "Hệ thống AI phân tích báo cáo tài chính doanh nghiệp niêm yết Việt Nam",
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="vi">
      <body>{children}</body>
    </html>
  )
}
