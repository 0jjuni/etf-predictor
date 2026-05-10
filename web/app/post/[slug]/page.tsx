import Link from "next/link";
import { notFound } from "next/navigation";
import { ChevronRight } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { getPost, listPosts } from "@/lib/posts";
import { formatKoreanDate, pct } from "@/lib/format";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export const revalidate = 600;
export const dynamicParams = true;

export async function generateStaticParams() {
  const posts = await listPosts();
  return posts.map((p) => ({ slug: p.slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const post = await getPost(slug);
  if (!post) return { title: slug };
  return {
    title: post.title,
    description: post.description,
  };
}

export default async function PostPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const post = await getPost(slug);
  if (!post) notFound();

  return (
    <div className="space-y-6">
      <nav className="flex items-center gap-1 text-xs text-slate-500 dark:text-slate-400">
        <Link href="/" className="hover:text-indigo-600">
          홈
        </Link>
        <ChevronRight className="h-3 w-3" />
        <Link href="/blog" className="hover:text-indigo-600">
          일일 분석
        </Link>
        <ChevronRight className="h-3 w-3" />
        <span className="text-slate-700 dark:text-slate-300">{post.date}</span>
      </nav>

      <header>
        <Badge variant="secondary">{formatKoreanDate(post.date)}</Badge>
        <h1 className="mt-3 text-3xl font-bold leading-tight tracking-tight">
          {post.title}
        </h1>
        {post.description && (
          <p className="mt-2 text-base text-slate-500 dark:text-slate-400">
            {post.description}
          </p>
        )}
      </header>

      {post.picks && post.picks.length > 0 && (
        <Card>
          <CardContent className="p-5">
            <div className="mb-3 text-[11px] font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
              오늘의 추천 종목
            </div>
            <div className="grid gap-2 sm:grid-cols-2">
              {post.picks.map((p) => (
                <Link
                  key={p.symbol}
                  href={`/etf/${p.symbol}`}
                  className="flex items-center justify-between rounded-lg border border-slate-200 px-3 py-2.5 transition hover:border-indigo-400 hover:bg-indigo-50/40 dark:border-slate-700 dark:hover:border-indigo-500 dark:hover:bg-indigo-500/10"
                >
                  <div className="min-w-0">
                    <div className="font-mono text-[11px] text-slate-400">
                      {p.symbol}
                    </div>
                    <div className="truncate text-sm font-medium">
                      {p.name}
                    </div>
                  </div>
                  <Badge variant="default" className="text-sm font-bold">
                    {pct(p.probability, 1)}
                  </Badge>
                </Link>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      <article className="prose prose-slate max-w-none dark:prose-invert">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{post.content}</ReactMarkdown>
      </article>

      <Card className="border-amber-200 bg-amber-50 dark:border-amber-500/30 dark:bg-amber-500/10">
        <CardContent className="p-4 text-xs text-amber-900 dark:text-amber-200">
          본 분석은 AI가 자동으로 작성한 정보 제공 목적의 글이며, 매수·매도
          권유가 아닙니다. 투자 결과의 책임은 전적으로 투자자 본인에게 있습니다.
        </CardContent>
      </Card>
    </div>
  );
}
