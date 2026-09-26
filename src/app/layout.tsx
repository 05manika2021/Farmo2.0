import type { Metadata } from 'next'
import './globals.css'
import { AppProvider } from '@/contexts/AppContext'

export const metadata: Metadata = {
  title: 'Farmo',
  description: 'AI-powered market intelligence for Indian farmers',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Poppins:ital,wght@0,400;0,500;0,600;0,700;0,800;1,400&display=swap" rel="stylesheet" />
      </head>
      <body>
        <AppProvider>
          <div className="min-h-screen bg-[#0A1A15] flex flex-col items-center justify-start py-6 px-4 gap-4">
            <div
              className="w-full max-w-[390px] bg-white rounded-[44px] overflow-hidden shadow-2xl relative"
              style={{ minHeight: '844px', maxHeight: '844px' }}
            >
              <div className="absolute inset-0 overflow-y-auto overflow-x-hidden no-scrollbar">
                {children}
              </div>
              <div className="absolute top-0 left-1/2 -translate-x-1/2 w-32 h-7 bg-black rounded-b-2xl z-50 pointer-events-none" />
            </div>
            <p className="text-white/20 text-xs">Farmo · AI Market Intelligence for Indian Farmers</p>
          </div>
        </AppProvider>
      </body>
    </html>
  )
}
