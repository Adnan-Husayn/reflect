import { NavLink } from "react-router-dom";

const links = [
  { to: "/", label: "Live session", end: true },
  { to: "/trends", label: "Trends", end: false },
];

export function AppNav() {
  return (
    <nav className="app-nav" aria-label="Main">
      {links.map(({ to, label, end }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          className={({ isActive }) => (isActive ? "app-nav-link active" : "app-nav-link")}
        >
          {label}
        </NavLink>
      ))}
    </nav>
  );
}
