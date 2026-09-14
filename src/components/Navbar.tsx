const NAV_LINKS = [
  { label: "How it works", href: "#how-it-works" },
  { label: "Compare", href: "#compare" },
  { label: "Results", href: "#results" },
] as const;

export function Navbar() {
  return (
    <nav
      data-testid="main-nav"
      aria-label="Main"
      className="flex items-center justify-between border-b border-slate-200 px-6 py-4"
    >
      <a href="/" className="text-lg font-semibold tracking-tight text-slate-900">
        Pairwise
      </a>

      <ul className="flex items-center gap-6">
        {NAV_LINKS.map((link) => (
          <li key={link.href}>
            <a
              href={link.href}
              className="text-sm text-slate-600 transition-colors hover:text-slate-900"
            >
              {link.label}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}
