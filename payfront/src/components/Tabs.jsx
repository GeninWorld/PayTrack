"use client";

import Link from "next/link";
import styles from "./tabs.module.css";

export default function Tabs({ items, activeHref, brand }) {
  return (
    <div className={styles.tabs}>
      <div className={styles.brand}>{brand}</div>
      <nav className={styles.tablist}>
        {items.map((it) => (
          <Link
            key={it.href}
            href={it.href}
            className={`${styles.tab} ${activeHref === it.href ? styles.tabActive : ""}`}
          >
            {it.label}
          </Link>
        ))}
      </nav>
    </div>
  );
}


