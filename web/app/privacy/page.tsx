export const metadata = { title: "개인정보 처리방침" };

export default function PrivacyPage() {
  return (
    <article className="prose prose-slate mx-auto max-w-3xl">
      <h1>개인정보 처리방침</h1>
      <p>
        ETF 종가 예측기는 회원가입·로그인 기능을 제공하지 않으며, 사용자로부터
        직접 식별 가능한 개인정보를 수집하지 않습니다.
      </p>
      <h2>1. 수집되는 정보</h2>
      <ul>
        <li>
          서버 접근 로그(IP, User-Agent, 타임스탬프) — 호스팅 제공자(Vercel,
          Supabase)의 인프라 운영 목적으로 임시 저장될 수 있습니다.
        </li>
        <li>
          향후 광고 게재 시: Google AdSense 등 제휴 광고 네트워크의 쿠키가
          사용될 수 있습니다.
        </li>
      </ul>
      <h2>2. 쿠키 / 로컬 스토리지</h2>
      <p>
        본 서비스는 운영 목적의 필수 쿠키 외에 추가 추적을 하지 않습니다. 광고
        네트워크가 통합되면 별도 고지 후 적용 예정입니다.
      </p>
      <h2>3. 외부 링크</h2>
      <p>
        본 서비스의 일부 콘텐츠(관련 기사 등)는 외부 사이트로 연결되며, 외부
        사이트의 개인정보 처리는 해당 사이트의 정책을 따릅니다.
      </p>
      <h2>4. 문의</h2>
      <p>
        개인정보 처리방침과 관련된 문의는{" "}
        <a href="https://github.com/0jjuni/etf-predictor/issues" target="_blank" rel="noopener noreferrer">
          GitHub 이슈
        </a>
        를 통해 남겨주세요.
      </p>
    </article>
  );
}
