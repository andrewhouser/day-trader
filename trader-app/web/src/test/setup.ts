import "@testing-library/jest-dom";
import { vi } from "vitest";

// Mock Next.js navigation
vi.mock("next/navigation", () => ({
  usePathname: vi.fn().mockReturnValue("/"),
  useRouter: vi.fn().mockReturnValue({
    back: vi.fn(),
    forward: vi.fn(),
    push: vi.fn(),
    refresh: vi.fn(),
    replace: vi.fn(),
  }),
  useSearchParams: vi.fn().mockReturnValue(new URLSearchParams()),
}));

// Mock Next.js Link
vi.mock("next/link", () => ({
  default: ({
    children,
    className,
    href,
    ...rest
  }: {
    children: React.ReactNode;
    className?: string;
    href: string;
    [key: string]: unknown;
  }) => (
    <a className={className} href={href} {...rest}>
      {children}
    </a>
  ),
}));

// Silence recharts ResizeObserver warnings in jsdom
global.ResizeObserver = class ResizeObserver {
  disconnect() {}
  observe() {}
  unobserve() {}
};
