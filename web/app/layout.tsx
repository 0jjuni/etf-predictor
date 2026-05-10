import type { Metadata } from "next";
import Link from "next/link";
import { ChartLine } from "lucide-react";
import { ThemeProvider } from "@/components/theme-provider";
import { ThemeToggle } from "@/components/theme-toggle";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "ETF 종가 예측기 · 한국 ETF 다음 거래일 +2.5% 상승 예측",
    template: "%s · ETF 종가 예측기",
  },
  description:
    "한국 ETF 중 다음 거래일 종가가 +2.5% 이상 오를 가능성이 높은 종목을 매일 자동으로 추천합니다. AI 모델이 매일 KST 08시에 학습합니다.",
  keywords: [
    "ETF",
    "한국 ETF",
    "ETF 추천",
    "ETF 예측",
    "주식 AI",
    "코스피 ETF",
    "ETF 시그널",
    "종가 예측",
  ],
  openGraph: {
    title: "ETF 종가 예측기",
    description:
      "한국 ETF 901개를 매일 학습해 다음 거래일 +2.5% 상승 후보를 추천합니다.",
    type: "website",
    locale: "ko_KR",
  },
  twitter: {
    card: "summary_large_image",
    title: "ETF 종가 예측기",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko" className="h-full antialiased" suppressHydrationWarning>
      <body className="min-h-full bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
        <ThemeProvider>
          <div className="flex min-h-full flex-col">
            <Header />
            <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-8 sm:py-12">
              {children}
            </main>
            <Footer />
          </div>
        </ThemeProvider>
      </body>
    </html>
  );
}

function Header() {
  return (
    <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/85 backdrop-blur dark:border-slate-800 dark:bg-slate-950/85">
      <nav className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
        <Link
          href="/"
          className="group flex items-center gap-2 text-base font-bold tracking-tight"
        >
          <span className="grid h-7 w-7 place-items-center rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600 text-white shadow-sm shadow-indigo-500/30">
            <ChartLine className="h-3.5 w-3.5" />
          </span>
          <span className="group-hover:text-indigo-600 dark:group-hover:text-indigo-400">
            ETF 종가 예측기
          </span>
        </Link>
        <div className="flex items-center gap-1">
          <ul className="flex items-center gap-1 text-sm text-slate-600 dark:text-slate-300">
            <NavLink href="/today" label="오늘" />
            <NavLink href="/blog" label="분석" />
            <NavLink href="/backtest" label="백테스트" />
            <NavLink href="/model" label="모델" />
          </ul>
          <div className="ml-1 border-l border-slate-200 pl-1 dark:border-slate-800">
            <ThemeToggle />
          </div>
        </div>
      </nav>
    </header>
  );
}

function NavLink({ href, label }: { href: string; label: string }) {
  return (
    <li>
      <Link
        className="rounded-md px-2.5 py-1.5 transition hover:bg-slate-100 hover:text-indigo-600 dark:hover:bg-slate-800 dark:hover:text-indigo-400 sm:px-3"
        href={href}
      >
        {label}
      </Link>
    </li>
  );
}

function Footer() {
  return (
    <footer className="border-t border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-950">
      <div className="mx-auto max-w-5xl px-4 py-8 text-xs text-slate-500 dark:text-slate-400">
        <p className="leading-relaxed">
          본 서비스는{" "}
          <strong className="text-slate-700 dark:text-slate-200">
            투자 판단의 보조 자료
          </strong>
          일 뿐이며 매수·매도 권유가 아닙니다. 투자 결과의 책임은 전적으로
          투자자 본인에게 있습니다.
        </p>
        <p className="mt-3 flex flex-wrap gap-x-4 gap-y-1.5">
          <Link
            className="hover:text-indigo-600 hover:underline dark:hover:text-indigo-400"
            href="/about"
          >
            소개
          </Link>
          <Link
            className="hover:text-indigo-600 hover:underline dark:hover:text-indigo-400"
            href="/disclaimer"
          >
            유의사항
          </Link>
          <Link
            className="hover:text-indigo-600 hover:underline dark:hover:text-indigo-400"
            href="/privacy"
          >
            개인정보
          </Link>
          <a
            className="hover:text-indigo-600 hover:underline dark:hover:text-indigo-400"
            href="https://github.com/0jjuni/etf-predictor"
            target="_blank"
            rel="noopener noreferrer"
          >
            GitHub
          </a>
        </p>
      </div>
    </footer>
  );
}
