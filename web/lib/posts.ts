import fs from "node:fs/promises";
import path from "node:path";
import matter from "gray-matter";

export interface PostFrontmatter {
  title: string;
  date: string;
  description?: string;
  picks?: { symbol: string; name: string; probability: number }[];
}

export interface Post extends PostFrontmatter {
  slug: string;
  content: string;
}

export const POSTS_DIR = path.join(process.cwd(), "content", "posts");

async function readSafe(): Promise<string[]> {
  try {
    return await fs.readdir(POSTS_DIR);
  } catch {
    return [];
  }
}

export async function listPosts(): Promise<Post[]> {
  const files = await readSafe();
  const posts: Post[] = [];
  for (const file of files) {
    if (!file.endsWith(".mdx") && !file.endsWith(".md")) continue;
    const slug = file.replace(/\.(mdx|md)$/, "");
    try {
      const post = await getPost(slug);
      if (post) posts.push(post);
    } catch {
      // Skip files that fail to parse rather than crashing the whole list.
    }
  }
  posts.sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : 0));
  return posts;
}

export async function getPost(slug: string): Promise<Post | null> {
  for (const ext of [".mdx", ".md"]) {
    const filePath = path.join(POSTS_DIR, `${slug}${ext}`);
    try {
      const raw = await fs.readFile(filePath, "utf-8");
      const { data, content } = matter(raw);
      return {
        slug,
        title: (data.title as string) ?? slug,
        date: (data.date as string) ?? slug,
        description: data.description as string | undefined,
        picks: data.picks as Post["picks"],
        content,
      };
    } catch {
      // try next extension
    }
  }
  return null;
}
