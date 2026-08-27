"use client";

import { FormEvent, useState } from "react";
import { createDemoSession } from "@/lib/api";

export function DemoAccessGate() {
  const [accessCode, setAccessCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [unlocking, setUnlocking] = useState(false);

  async function unlock(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setUnlocking(true);
    setError(null);
    try {
      await createDemoSession(accessCode);
      window.location.reload();
    } catch {
      setError("访问码无效，请重新输入。");
      setUnlocking(false);
    }
  }

  return (
    <main className="grid min-h-screen place-items-center bg-[#f4f1e9] p-6 text-[#17231d]">
      <form
        className="w-full max-w-md rounded-3xl border border-[#d8d3c7] bg-white p-8 shadow-sm"
        onSubmit={unlock}
      >
        <p className="text-sm font-semibold text-[#7b4f2f]">PROTECTED DEMO</p>
        <h1 className="mt-2 text-3xl font-semibold">访问 ResearchFlow</h1>
        <p className="mt-3 text-sm leading-6 text-[#6d746f]">
          请输入作品集演示访问码。访问码只发送给后端，不会写入浏览器包。
        </p>
        <input
          aria-label="演示访问码"
          autoComplete="current-password"
          className="mt-6 w-full rounded-2xl border border-[#cfc9bd] px-4 py-3 outline-none focus:border-[#2f6f5e]"
          onChange={(event) => setAccessCode(event.target.value)}
          required
          type="password"
          value={accessCode}
        />
        <button
          className="mt-4 w-full rounded-full bg-[#2f6f5e] px-5 py-3 font-semibold text-white disabled:opacity-50"
          disabled={unlocking}
          type="submit"
        >
          {unlocking ? "正在验证…" : "进入演示"}
        </button>
        {error && <p className="mt-4 text-sm text-red-700">{error}</p>}
      </form>
    </main>
  );
}
