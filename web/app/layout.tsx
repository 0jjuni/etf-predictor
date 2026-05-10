import type { Metadata } from "next";
import Link from "next/link";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  variable: "--font-sans",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: {
    default: "ETF 종가 예측기",
    template: "%s · ETF 종가 예측기",
  },
  description:
    "한국 ETF 중 다음 거래일 종가가 +2.5% 이상 오를 가능성이 높은 종목을 매일 자동으로 추천합니다. AI 모델이 매일 KST 08시에 학습합니다.",
  keywords: ["ETF", "한국 ETF", "ETF 추천", "ETF 예측", "주식 AI", "코스피 ETF"],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="ko"
      className={`${inter.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-slate-50 text-slate-900">
        <header className="border-b border-slate-200 bg-white">
          <nav className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
            <Link href="/" className="text-base font-bold tracking-tight">
              ETF 종가 예측기
            </Link>
            <ul className="flex items-center gap-4 text-sm text-slate-600">
              <li>
                <Link className="hover:text-indigo-600" href="/today">
                  오늘
                </Link>
              </li>
              <li>
                <Link className="hover:text-indigo-600" href="/backtest">
                  백테스트
                </Link>
              </li>
              <li>
                <Link className="hover:text-indigo-600" href="/model">
                  모델
                </Link>
              </li>
            </ul>
          </nav>
        </header>
        <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-8">
          {children}
        </main>
        <footer className="border-t border-slate-200 bg-white">
          <div className="mx-auto max-w-5xl px-4 py-6 text-xs text-slate-500">
            <p>
              본 서비스는 <strong>투자 판단의 보조 자료</strong>일 뿐이며 매수·매도
              권유가 아닙니다. 투자 결과의 책임은 전적으로 투자자 본인에게
              있습니다.
            </p>
            <p className="mt-2 flex flex-wrap gap-x-3">
              <Link className="hover:underline" href="/about">
                소개
              </Link>
              <Link className="hover:underline" href="/disclaimer">
                유의사항
              </Link>
              <Link className="hover:underline" href="/privacy">
                개인정보
              </Link>
              <a
                className="hover:underline"
                href="https://github.com/0jjuni/etf-predictor"
                target="_blank"
                rel="noopener noreferrer"
              >
                GitHub
              </a>
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
