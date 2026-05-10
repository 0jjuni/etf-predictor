import Link from "next/link";
import { ChevronRight } from "lucide-react";
import { listPosts } from "@/lib/posts";
import { formatKoreanDate } from "@/lib/format";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export const revalidate = 600;

export const metadata = {
  title: "일일 분석",
  description: "AI가 매일 작성하는 ETF 시장 분석 + 추천 종목 리포트.",
};

export default async function BlogIndexPage() {
  const posts = await listPosts();

  return (
    <div className="space-y-6">
      <nav className="flex items-center gap-1 text-xs text-slate-500 dark:text-slate-400">
        <Link href="/" className="hover:text-indigo-600">
          홈
        </Link>
        <ChevronRight className="h-3 w-3" />
        <span className="text-slate-700 dark:text-slate-300">일일 분석</span>
      </nav>

      <header>
        <h1 className="text-2xl font-bold tracking-tight">일일 분석</h1>
        <p className="mt-1 max-w-2xl text-sm text-slate-500 dark:text-slate-400">
          AI가 매일 학습 직후 자동으로 작성한 시장 분석과 추천 코멘터리입니다.
        </p>
      </header>

      {posts.length === 0 ? (
        <Card>
          <CardContent className="py-10 text-center">
            <p className="text-sm font-semibold text-slate-700 dark:text-slate-200">
              아직 발행된 포스트가 없어요.
            </p>
            <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
              매일 KST 08시 이후 자동 발행됩니다.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-3">
          {posts.map((p) => (
            <Link key={p.slug} href={`/post/${p.slug}`} className="group">
              <Card className="transition group-hover:border-indigo-400 group-hover:shadow-md">
                <CardContent className="p-5">
                  <div className="flex items-baseline justify-between gap-3">
                    <Badge variant="secondary">{formatKoreanDate(p.date)}</Badge>
                    {p.picks && p.picks.length > 0 && (
                      <span className="text-xs text-slate-500 dark:text-slate-400">
                        {p.picks.length}개 추천
                      </span>
                    )}
                  </div>
                  <h2 className="mt-2 text-lg font-semibold tracking-tight group-hover:text-indigo-600 dark:group-hover:text-indigo-400">
                    {p.title}
                  </h2>
                  {p.description && (
                    <p className="mt-1 line-clamp-2 text-sm text-slate-500 dark:text-slate-400">
                      {p.description}
                    </p>
                  )}
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
