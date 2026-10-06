import Link from "next/link";

const NAV_LINKS = [
  { href: "/how-it-works", label: "How it works" },
  { href: "/about", label: "About" },
] as const;

export function SiteHeader() {
  return (
    <header className="mx-auto flex w-full max-w-6xl items-center justify-between px-5 py-5 sm:px-8">
      <Link
        href="/"
        className="rounded-md font-heading text-lg font-semibold tracking-tight focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none"
      >
        AI Travel Universe
      </Link>
      <nav aria-label="Main">
        <ul className="flex items-center gap-1 text-sm">
          {NAV_LINKS.map((link) => (
            <li key={link.href} className="hidden sm:block">
              <Link
                href={link.href}
                className="rounded-md px-3 py-2 text-muted-foreground transition-colors hover:text-foreground focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none"
              >
                {link.label}
              </Link>
            </li>
          ))}
          <li>
            <Link
              href="/login"
              className="rounded-full px-4 py-2 font-medium transition-colors hover:bg-muted focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none"
            >
              Sign in
            </Link>
          </li>
        </ul>
      </nav>
    </header>
  );
}
